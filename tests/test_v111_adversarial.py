"""Adversariale Tests zu v1.11.0: Grenzfälle für Fenster-Limit, Tab-Events pro Fenster,
sanftes Scrollen (Abbruch durch Nutzer), Strg+Umschalt+W-Regeln und Themen-Modus."""
import random

import pytest

from awaketoggle import browse, queries
from awaketoggle.browse import (MAX_WINDOWS, TAB_LIMIT, WINDOW_LIMIT, Builder, Model, Person, _tidy_windows, _search,
                                 limit, make_scenario)
from awaketoggle.browse_runner import Abort, Runner
from awaketoggle.config import Config
from tests.test_browse import USER, FakeDesk
from tests.test_v111 import TabDesk, _plans, _runner_with_own_window


# ---------- Fenster-Limit: _tidy_windows / _do_close_window ----------

def test_tidy_windows_closes_oldest_from_front_of_wins_list():
    """Älteste eigenes Fenster steht an wins[0]; _tidy_windows mit way='aeltestes' muss wins[0] poppen."""
    rng = random.Random(0)
    b = Builder(rng, "normal")
    m = Model(person=Person.random(rng), win_limit=2)
    for _ in range(3):
        browse._new_window(b, m, rng)
    first_win = m.wins[0]
    # erzwinge "aeltestes" indem last_win_tidy='aktuelles' gesetzt wird und random() < 0.6
    m.last_win_tidy = "aktuelles"
    _tidy_windows(b, m, random.Random(7))  # seed 7 -> rng.random() < 0.6 → "aeltestes"
    assert m.wins[0] is not first_win  # ältestes weg
    assert len(m.wins) == 2


def test_tidy_windows_never_pops_below_one_window():
    rng = random.Random(0)
    b = Builder(rng, "normal")
    m = Model(person=Person.random(rng), win_limit=1)
    browse._new_window(b, m, rng)
    _tidy_windows(b, m, rng)
    assert len(m.wins) >= 1


def test_plan_opened_equals_closed_windows_across_many_seeds():
    for seed, plan in _plans(400, actions=100):
        opened = sum(1 for _, st in plan.steps for s in st if s[0] == "new_window")
        closed = sum(1 for _, st in plan.steps for s in st if s[0] == "close_window")
        assert opened == closed, (seed, opened, closed)
        assert opened >= 1


def test_runner_close_oldest_when_oldest_has_foreign_tab_keeps_it_open():
    """Ältestes eigenes Fenster hat einen fremden Tab -> wird nicht komplett geschlossen,
    bleibt offen (fremder Tab unangetastet). Nutzerfenster unberührt."""
    desk = TabDesk()
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(0))
    r._cancel, r._opened = (lambda: False), True
    h1 = desk._open()
    desk.wins[h1]["tabs"] = 3
    h2 = desk._open()
    desk.wins[h2]["tabs"] = 2
    r._stack = [h1, h2]
    # h1 hat fremden Tab (nicht in own)
    ids1 = {t for t, _ in desk.tabs(h1)}
    r._own_tabs[h1] = {t for t in ids1 if not t.endswith("-own-0")}
    r._own_tabs[h2] = {t for t, _ in desk.tabs(h2)}
    r._mark()
    # Rotation: ältestes (h1) nach vorn, dann _close_top
    r._do_close_window("oldest")
    # h1 bleibt offen wegen fremdem Tab
    assert h1 in desk.wins
    # Kein Strg+Umschalt+W an h1
    assert ("ctrl+shift+w", h1) not in [(k, w) for w, k in desk.sent]
    assert not any(w == h1 and k == "ctrl+shift+w" for w, k in desk.sent)
    # Nutzerfenster komplett unberührt
    assert USER in desk.wins and desk.wins[USER]["tabs"] == 3
    assert not any(w == USER for w, _ in desk.sent)


def test_runner_never_sends_ctrl_shift_w_to_user_window_across_full_runs():
    for seed in range(60):
        desk = FakeDesk()
        plan = make_scenario(Config(signal="browse", browse_actions_max=30), random.Random(seed))
        res = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(seed)).run(plan, ())
        assert res.status == "done"
        assert not any(w == USER and k == "ctrl+shift+w" for w, k in desk.sent), seed


def test_ctrl_shift_w_not_sent_when_tabs_unreadable():
    """FakeDesk.tabs() liefert None -> _own_tabs leer -> _all_tabs_own False -> Fallback Ctrl+W."""
    desk = FakeDesk()
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(0))
    r._cancel, r._opened = (lambda: False), True
    h = desk._open()
    desk.wins[h]["tabs"] = 2
    r._stack = [h]
    # _own_tabs leer lassen: Fenster unverfolgt
    r._mark()
    r._close_top()
    assert "ctrl+shift+w" not in [k for _, k in desk.sent]
    assert h not in desk.wins  # mit ctrl+w einzeln geschlossen


# ---------- _tab_events pro Fenster ----------

def test_tab_events_are_isolated_per_window():
    """Fix: Eigener Tab-Event in Fenster A darf NICHT einen neuen Tab in Fenster B als eigen zählen."""
    desk = TabDesk()
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(0))
    r._cancel, r._opened = (lambda: False), True
    h1 = desk._open()
    desk.wins[h1]["tabs"] = 2
    h2 = desk._open()
    desk.wins[h2]["tabs"] = 2
    r._stack = [h1, h2]
    r._own_tabs[h1] = {t for t, _ in desk.tabs(h1)}
    r._own_tabs[h2] = {t for t, _ in desk.tabs(h2)}
    # In h1 wird gleich ein neuer Tab aufgehen → Event für h1 anlegen
    r._tab_events[h1] = [desk.clock()]
    # In h2 taucht ein fremder Tab auf (ohne eigenes Event für h2)
    desk.ids[h2].append(f"{h2}-foreign-1")
    desk.wins[h2]["tabs"] += 1
    tabs = r._tabs(h2)
    assert tabs is not None
    # Fremder Tab darf nicht als eigen übernommen worden sein
    assert f"{h2}-foreign-1" not in r._own_tabs[h2]
    assert f"{h2}-foreign-1" in r._foreign_tabs
    # Event in h1 ist unangetastet
    assert len(r._tab_events[h1]) == 1


def test_own_tab_event_in_same_window_is_consumed():
    desk = TabDesk()
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(0))
    r._cancel, r._opened = (lambda: False), True
    h = desk._open()
    desk.wins[h]["tabs"] = 2
    r._stack = [h]
    r._own_tabs[h] = {t for t, _ in desk.tabs(h)}
    r._tab_events[h] = [desk.clock()]
    # neuer Tab erscheint in h, direkt nach eigenem Event
    desk.ids[h].append(f"{h}-own-new")
    desk.wins[h]["tabs"] += 1
    r._tabs(h)
    assert f"{h}-own-new" in r._own_tabs[h]
    assert f"{h}-own-new" not in r._foreign_tabs
    assert r._tab_events[h] == []  # Event verbraucht


# ---------- Sanftes Scrollen ----------

def test_scroll_aborts_mid_delta_when_cancel_triggers():
    """_do_scroll prüft vor jedem Rad-Tick auf Abbruch (Nutzeraktivität / Toggle aus)."""
    desk = FakeDesk()
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(0))
    calls = {"n": 0}
    def cancel():
        calls["n"] += 1
        return calls["n"] > 2  # ab 3. Prüfung: abbrechen
    r._cancel = cancel
    r._mark()
    wheels = []
    orig = desk.wheel
    def wheel(d, orig=orig):
        wheels.append(d)
        orig(d)
    desk.wheel = wheel
    deltas = (10, 20, 30, 40, 50)
    gaps = (0.01, 0.01, 0.01, 0.01, 0.01)
    with pytest.raises(Abort):
        r._do_scroll(deltas, gaps)
    assert 0 < len(wheels) < len(deltas)  # mittendrin abgebrochen


def test_scroll_sequence_monotonic_direction_and_bounded_deltas():
    """Jedes scroll-Event: alle Deltas in gleiche Richtung, Betrag < 120, Anzahl Deltas == Gaps."""
    seen = 0
    for _, plan in _plans(80, actions=60):
        for _, steps in plan.steps:
            for s in steps:
                if s[0] != "scroll":
                    continue
                deltas, gaps = s[1], s[2]
                assert len(deltas) == len(gaps) >= 3
                assert all(d != 0 for d in deltas)
                assert all(abs(d) < 120 for d in deltas)
                signs = {d > 0 for d in deltas}
                assert len(signs) == 1  # einheitliche Richtung
                assert all(g > 0 for g in gaps)
                seen += 1
    assert seen > 50


# ---------- Themen-Modus ----------

def test_bunt_mode_switches_theme_more_often_than_ein_thema():
    def switches(topic):
        rng = random.Random(42)
        b = Builder(rng, "normal")
        m = Model(person=Person.random(rng), topic=topic)
        browse._new_window(b, m, rng)
        prev = None
        n = 0
        for _ in range(40):
            _search(b, m, rng)
            if prev is not None and m.interest.theme != prev:
                n += 1
            prev = m.interest.theme
        return n
    bunt = switches("bunt")
    one = switches("ein_thema")
    assert one == 0 and bunt >= 5


def test_related_theme_falls_back_when_unknown():
    rng = random.Random(0)
    assert queries.related_theme("gibtsnicht", rng) in queries.THEMES


def test_interest_next_does_not_repeat_queries_over_long_sequence():
    for seed in range(80):
        it = queries.Interest(random.Random(seed), "rezept", budget=20)
        seen = [it.first()]
        for _ in range(15):
            seen.append(it.next())
        # mind. 90% unterschiedlich (nicht alle neu, da _fresh scheitert kann)
        assert len(set(seen)) >= len(seen) - 2, (seed, seen)


def test_interest_again_stays_within_theme():
    for seed in range(30):
        it = queries.Interest(random.Random(seed), "wetter", budget=10)
        it.first()
        for _ in range(5):
            it.again()
            # kein harter Themenwechsel in again
        assert it.theme == "wetter"


# ---------- WINDOW/TAB-Limit Sanity ----------

def test_window_limit_mode_is_within_bounds():
    assert WINDOW_LIMIT[0] <= browse.WINDOW_LIMIT_MODE <= WINDOW_LIMIT[1]
    assert TAB_LIMIT[0] <= browse.TAB_LIMIT_MODE <= TAB_LIMIT[1]
    assert MAX_WINDOWS == WINDOW_LIMIT[1] + 1


def test_make_scenario_label_contains_topic_mode():
    for seed in range(20):
        plan = make_scenario(Config(signal="browse", browse_actions_max=20), random.Random(seed))
        parts = plan.label.split(", ")
        assert parts[2] in ("ein Thema", "Themenkette", "bunt")


# ---------- ctrl+shift+w nie als Keystroke in Plänen ----------

def test_no_blocked_window_close_shortcut_in_any_plan():
    for _, plan in _plans(200, actions=50):
        for _, steps in plan.steps:
            for s in steps:
                if s[0] in ("key", "nav", "new_window"):
                    assert s[1] != "ctrl+shift+w"


# ---------- Reuse der TabDesk-Fixtures ----------

def test_tabdesk_window_with_only_own_tabs_closes_at_once_regression():
    desk = TabDesk()
    r, h = _runner_with_own_window(desk)
    r._close_top()
    assert h not in desk.wins
    assert "ctrl+shift+w" in [k for _, k in desk.sent]
