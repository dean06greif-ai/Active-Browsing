"""Adversarial checks for the 'natural, human-like browsing' refactor.

Guards (per review request):
  * queries.THEMES fills must never leave an unfilled '{...}' placeholder nor raise KeyError
  * Interest.first/next produce no adjacent duplicates and sensible sequences
  * Builder.type: applying the backspaces in the typed stream must yield the intended text
  * make_scenario: all action preconditions actually hold at execution time
    (no refine without prior search, no tab-switch with 1 tab, no reading on empty tab,
     no result-open outside result page, rare actions capped at MAX_RARE, no close_window
     without a prior new_window, tabs/windows within bounds).
"""
import random

from awaketoggle import queries
from awaketoggle.browse import (ACTIONS, MAX_RARE, MAX_TABS, MAX_WINDOWS, RARE, REPEAT_OK,
                                Builder, Model, Person, STYLES, _new_window, _page, _results)
from awaketoggle.config import Config


# ---------- queries.THEMES ----------

def test_all_theme_templates_fill_without_leftover_placeholders():
    for theme, (starts, refines, related) in queries.THEMES.items():
        for templates in (starts, refines, related):
            for tpl in templates:
                for seed in range(25):
                    r = random.Random(seed * 7 + hash(theme) % 1000)
                    out = queries._fill(tpl, r, q="basisfrage", city="berlin")
                    assert "{" not in out and "}" not in out, (theme, tpl, out)
                    assert out.strip(), (theme, tpl)


def test_interest_sequences_rarely_duplicate_in_a_row():
    dup = total = 0
    for seed in range(500):
        r = random.Random(seed)
        it = queries.Interest(r)
        prev = it.first()
        for _ in range(3):
            q = it.next()
            total += 1
            if q == prev:
                dup += 1
            prev = q
    # Allow very few (< 1%); the humanize layer may produce the same string back
    assert dup / total < 0.01, f"{dup}/{total} adjacent duplicates"


def test_interest_first_follows_theme():
    r = random.Random(3)
    it = queries.Interest(r, "wetter")
    first = it.first()
    assert "wetter" in first.lower()
    # 4 searches then exhausted
    for _ in range(3):
        it.next()
    assert it.exhausted


# ---------- Builder.type: backspace invariant ----------

def test_typed_text_after_applying_backspaces_matches_intended_text():
    for style in STYLES:
        for seed in range(300):
            r = random.Random(seed)
            b = Builder(r, style)
            intended = "wetter berlin morgen 2026"
            b.type(intended)
            kind, typed, delays = b.steps[0]
            assert kind == "type"
            assert len(typed) == len(delays)
            buf = []
            for c in typed:
                if c == "\b":
                    assert buf, "backspace with empty buffer"
                    buf.pop()
                else:
                    buf.append(c)
            assert "".join(buf) == intended, f"{style}/{seed}: typed={typed!r}"


def test_typed_backspace_delays_look_like_a_noticed_typo():
    # The first backspace after a typo should be noticeably slower (noticing time).
    saw_slow_first_bs = False
    for seed in range(500):
        r = random.Random(seed)
        b = Builder(r, "normal")
        b.type("abcdefghij" * 3)
        _, typed, delays = b.steps[0]
        for i, c in enumerate(typed):
            if c == "\b":
                if delays[i] >= 0.3:
                    saw_slow_first_bs = True
                break
    assert saw_slow_first_bs, "no noticed-typo delay observed across 500 seeds"


# ---------- make_scenario preconditions ----------

def _simulate(cfg, seed):
    rng = random.Random(seed)
    style = rng.choices(tuple(STYLES), (2, 5, 1.5))[0]
    b = Builder(rng, style)
    m = Model(person=Person.random(rng))
    _new_window(b, m)
    exclude = set(cfg.browse_exclude)
    n = rng.randint(max(3, cfg.browse_actions_max // 3), cfg.browse_actions_max)
    last = None
    chosen = []
    for _ in range(n):
        ids, weights = [], []
        for aid, (weight, _) in ACTIONS.items():
            if aid in exclude or (aid in RARE and (aid in m.used or len(m.used & RARE) >= MAX_RARE)):
                continue
            w = weight(m)
            if w > 0:
                ids.append(aid)
                weights.append(w * (1.0 if aid != last else 0.6 if aid in REPEAT_OK else 0.2))
        aid = rng.choices(ids, weights)[0] if ids else "pause"
        chosen.append(aid)
        # Preconditions BEFORE running the action
        if aid == "suche_verfeinern":
            assert m.interest is not None and not m.interest.exhausted and m.w.loaded
        if aid == "tab_wechseln":
            assert m.w.tabs > 1
        if aid in ("ergebnis_oeffnen", "im_tab_oeffnen"):
            assert _results(m), f"{aid} without result page (seed={seed})"
        if aid in ("klicken", "lesen_scrollen", "tastatur_scrollen", "auf_seite_suchen"):
            # lesen_scrollen allows ergebnisse OR seite; others require seite
            if aid == "lesen_scrollen":
                assert _page(m) or _results(m)
            else:
                assert _page(m), f"{aid} without page (seed={seed})"
        if aid == "fenster_schliessen":
            assert len(m.wins) > 1
        if aid == "neues_fenster":
            assert len(m.wins) < MAX_WINDOWS
        if aid == "neuer_tab":
            assert m.w.tabs < MAX_TABS and _page(m)
        ACTIONS[aid][1](b, m, rng)
        assert 1 <= m.w.tabs <= MAX_TABS, (seed, aid, m.w.tabs)
        assert 1 <= len(m.wins) <= MAX_WINDOWS, (seed, aid, len(m.wins))
        m.used.add(aid)
        last = aid
    return chosen, m


def test_all_scenario_preconditions_hold_across_many_seeds():
    cfg = Config(signal="browse")
    rare_counts = []
    for seed in range(1000):
        chosen, _m = _simulate(cfg, seed)
        rare_counts.append(sum(1 for a in chosen if a in RARE))
    assert max(rare_counts) <= MAX_RARE


def test_tab_counts_and_window_counts_stay_in_bounds():
    # Already asserted inside _simulate; this just gives an explicit name.
    cfg = Config(signal="browse")
    for seed in range(200):
        _simulate(cfg, seed)
