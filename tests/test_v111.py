"""v1.11.0: lockeres Tab-Limit (5–18), Fenster-Limit nur für eigene Fenster, sanftes Scrollen, Themenketten."""
import random

from awaketoggle import browse, queries
from awaketoggle.browse import (MAX_TABS, MAX_WINDOWS, TAB_LIMIT, WINDOW_LIMIT, Builder, Model, Person, _refine,
                                _search, limit, make_scenario)
from awaketoggle.browse_runner import Runner
from awaketoggle.config import Config
from tests.test_browse import USER, FakeDesk


def _plans(n, actions=80):
    for seed in range(n):
        yield seed, make_scenario(Config(signal="browse", browse_actions_max=actions), random.Random(seed))


def test_tab_and_window_limits_are_random_but_natural():
    rng = random.Random(1)
    tabs = [limit(rng, *TAB_LIMIT, browse.TAB_LIMIT_MODE) for _ in range(3000)]
    wins = [limit(rng, *WINDOW_LIMIT, browse.WINDOW_LIMIT_MODE) for _ in range(3000)]
    assert min(tabs) == 5 and max(tabs) >= 16 and 7 <= sorted(tabs)[1500] <= 12
    assert min(wins) == 2 and max(wins) == 4 and sorted(wins)[1500] <= 3
    assert MAX_TABS == 19 and MAX_WINDOWS == 5


def test_plan_window_model_stays_within_own_window_limit():
    oldest = tidy = 0
    for seed, plan in _plans(200):
        open_ = 0
        for name, steps in plan.steps:
            tidy += name == "alte_fenster_schliessen"
            for s in steps:
                if s[0] == "new_window":
                    open_ += 1
                elif s[0] == "close_window":
                    open_ -= 1
                    oldest += s[1:] == ("oldest",)
                assert 0 <= open_ <= MAX_WINDOWS, seed
        assert open_ == 0
    assert tidy > 10 and oldest > 5


def test_runner_closes_oldest_own_window_never_user_window():
    done = 0
    for seed, plan in _plans(60):
        if not any(s[1:] == ("oldest",) for _, st in plan.steps for s in st if s[0] == "close_window"):
            continue
        desk = FakeDesk()
        res = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(seed)).run(plan, ())
        assert res.status == "done", (seed, res)
        assert set(desk.wins) == {USER} and desk.wins[USER]["tabs"] == 3
        assert [k for h, k in desk.sent if h == USER] == ["ctrl+n"]
        done += 1
    assert done >= 3


class TabDesk(FakeDesk):
    """Tableiste lesbar: jedes Fenster hat Tab-IDs; Strg+Umschalt+W schließt das ganze Fenster."""

    def __init__(self, foreign=False):
        super().__init__()
        self.ids = {}
        self.foreign = foreign

    def tabs(self, h):
        if h not in self.wins:
            return None
        ids = self.ids.setdefault(h, [f"{h}-own-{i}" for i in range(self.wins[h]["tabs"])])
        return [(t, i == len(ids) - 1) for i, t in enumerate(ids)]

    def send_combo(self, vks):
        name = "+".join(browse_names(v) for v in vks)
        h = self.foreground()
        if name == "ctrl+shift+w" and h in self.wins:
            self._input()
            self.sent.append((h, name))
            self._close(h)
            return
        super().send_combo(vks)
        if h in self.wins and name in ("ctrl+w", "ctrl+f4") and self.ids.get(h):
            self.ids[h].pop()


def browse_names(v):
    from tests.test_browse import NAMES
    return NAMES[v]


def _runner_with_own_window(desk, foreign=False):
    h = desk._open()
    desk.wins[h]["tabs"] = 4
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(1))
    r._cancel, r._opened, r._stack = (lambda: False), True, [h]
    ids = {t for t, _ in desk.tabs(h)}
    if foreign:
        ids.discard(f"{h}-own-0")
    r._own_tabs[h] = ids
    r._mark()
    return r, h


def test_window_with_only_own_tabs_is_closed_at_once():
    desk = TabDesk()
    r, h = _runner_with_own_window(desk)
    r._close_top()
    assert h not in desk.wins and r._stack == []
    assert [k for w, k in desk.sent if w == h] == ["ctrl+shift+w"]


def test_window_with_foreign_tab_is_never_closed_at_once():
    desk = TabDesk()
    r, h = _runner_with_own_window(desk, foreign=True)
    r._close_top()
    assert "ctrl+shift+w" not in [k for _, k in desk.sent]
    assert h in desk.wins  # fremder Tab bleibt, Fenster bleibt offen
    assert USER in desk.wins and desk.wins[USER]["tabs"] == 3


def test_ctrl_shift_w_never_in_plans():
    for _, plan in _plans(150):
        assert all(s[1] != "ctrl+shift+w" for _, st in plan.steps for s in st if s[0] in ("key", "nav"))


def test_scrolling_is_smooth():
    flicks = 0
    for _, plan in _plans(60):
        for _, steps in plan.steps:
            for s in steps:
                assert s[0] != "wheel"
                if s[0] != "scroll":
                    continue
                deltas, gaps = s[1], s[2]
                assert len(deltas) == len(gaps) >= 3
                assert all(abs(d) < 120 for d in deltas)
                assert len({d > 0 for d in deltas}) == 1
                if len(deltas) >= 5 and all(g < 0.05 for g in gaps):  # Schwung: sanft an- und auslaufen
                    flicks += 1
                    mid = abs(deltas[len(deltas) // 2])
                    assert abs(deltas[0]) <= mid and abs(deltas[-1]) <= mid
    assert flicks > 100


def _model(topic, seed=0):
    rng = random.Random(seed)
    b = Builder(rng, "normal")
    m = Model(person=Person.random(rng), topic=topic)
    browse._new_window(b, m, rng)
    return b, m, rng


def test_one_topic_session_stays_in_one_theme():
    for seed in range(30):
        b, m, rng = _model("ein_thema", seed)
        themes = set()
        for _ in range(25):
            (_refine if m.interest and not m.interest.exhausted and rng.random() < 0.6 else _search)(b, m, rng)
            themes.add(m.interest.theme)
        assert len(themes) == 1, (seed, themes)


def test_chain_stays_4_to_8_searches_then_mostly_related_theme():
    related = switches = 0
    for seed in range(60):
        b, m, rng = _model("kette", seed)
        _search(b, m, rng)
        for _ in range(40):
            it = m.interest
            assert 4 <= it.budget <= 8
            if it.exhausted:
                _search(b, m, rng)
                if m.interest is not it:
                    switches += 1
                    related += m.interest.theme in queries.RELATED[it.theme] or m.interest.theme == it.theme
            else:
                _refine(b, m, rng)
    assert switches > 100 and related / switches > 0.55


def test_refinements_build_on_each_other_without_repeats():
    built = 0
    for seed in range(200):
        it = queries.Interest(random.Random(seed), "rezept", budget=8)
        it.first()
        prev = it.anchor
        seen = [it.query]
        for _ in range(7):
            it.next()
            built += it.query.startswith(prev.split(" = ")[0]) and it.query != prev
            prev = it.anchor
            seen.append(it.query)
        assert len(set(seen)) >= len(seen) - 1, seen
    assert built > 400


def test_many_themes_with_related_map():
    assert len(queries.THEMES) >= 60
    assert set(queries.RELATED) == set(queries.THEMES)
    for t, rel in queries.RELATED.items():
        assert rel and all(r in queries.THEMES and r != t for r in rel), t
    names = set()
    for _, plan in _plans(60, 20):
        names.add(plan.label.split(", ")[2])
    assert names == {"ein Thema", "Themenkette", "bunt"}
