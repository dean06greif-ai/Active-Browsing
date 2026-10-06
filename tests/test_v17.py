import random

from awaketoggle.browse import MAX_TABS, make_scenario
from awaketoggle.browse_runner import Result, Runner
from awaketoggle.config import Config, validate
from tests.test_browse import NAMES, USER, FakeDesk
from tests.test_core import make

NEXT = ("ctrl+tab", "ctrl+pgdn")
PREV = ("ctrl+shift+tab", "ctrl+pgup")
SWITCH = set(NEXT + PREV) | {f"ctrl+{i}" for i in range(1, 10)}


# ---------- Lange Pausen im Plan ----------

def _breaks(plan):
    return [(i, s[1]) for i, (_, st) in enumerate(plan.steps) for s in st if s[0] == "break"]


def test_scenario_has_one_long_break_in_the_middle_only_when_asked():
    for seed in range(200):
        cfg = Config(signal="browse", browse_actions_max=30)
        assert _breaks(make_scenario(cfg, random.Random(seed))) == []
        plan = make_scenario(cfg, random.Random(seed), pause_s=420)
        found = _breaks(plan)
        assert len(found) == 1 and found[0][1] == 420
        idx = found[0][0]
        assert plan.steps[idx][0] == "lange_pause"
        assert 1 < idx < len(plan.steps) - 1  # nie gleich am Anfang, nie beim Aufräumen
        assert "lange Pause 7 min" in plan.label


def _run(desk, seed, pause_s=None, cfg=None):
    cfg = cfg or Config(signal="browse", browse_actions_max=12)
    plan = make_scenario(cfg, random.Random(seed), pause_s=pause_s)
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(seed))
    return runner, runner.run(plan, ())


def test_long_break_minimizes_own_window_waits_and_restores_it():
    for seed in range(15):
        desk = FakeDesk()
        mins = []
        orig = desk.minimize

        def minimize(h, orig=orig):
            mins.append((h, desk.ms))
            return orig(h)
        desk.minimize = minimize
        t0 = desk.ms
        _, res = _run(desk, seed, pause_s=300)
        assert res.status == "done", (seed, res)
        assert mins and all(h != USER for h, _ in mins)  # nur eigene Fenster
        assert desk.ms - t0 >= 300_000
        assert set(desk.wins) == {USER} and not desk.wins[USER].get("min")
        assert [k for h, k in desk.sent if h == USER] == ["ctrl+n"]


def test_long_break_without_minimize_just_waits():
    desk = FakeDesk()
    desk.minimize_ok = False
    t0 = desk.ms
    _, res = _run(desk, 3, pause_s=200)
    assert res.status == "done" and desk.ms - t0 >= 200_000
    assert set(desk.wins) == {USER}


def test_user_coming_back_during_long_break_aborts_at_once():
    desk = FakeDesk(user_input_at_ms=1_000_000 + 120_000)
    _, res = _run(desk, 4, pause_s=900)
    assert res.status == "aborted" and res.text == "Sie sind aktiv"
    assert desk.ms < 1_000_000 + 130_000  # + 6 s passives Nachführen der Fenstertitel


def test_config_break_and_chain_keys():
    cfg, w = validate({"browse_breaks": False, "browse_break_minutes": [3, 8], "browse_break_every_minutes": [30, 90],
                       "browse_chain_percent": 25})
    assert w == [] and not cfg.browse_breaks and cfg.browse_break_minutes == (3, 8)
    assert cfg.browse_break_every_minutes == (30, 90) and cfg.browse_chain_percent == 25
    cfg, w = validate({"browse_break_minutes": [10, 2], "browse_break_every_minutes": [5], "browse_chain_percent": 150})
    assert len(w) == 3 and cfg == Config()


# ---------- Engine: Pausen nach langem Betrieb, Sitzungen ohne Abstand ----------

def _engine(cfg):
    api, clock, eng = make(cfg, rng=random.Random(1))
    plans = []

    def browse(plan, cfg, cancel):
        plans.append(plan)
        api.last = api.now
        return Result("done", "ok")
    api.browse = browse
    eng.set_active(True)
    return api, clock, eng, plans


def test_long_break_comes_only_after_long_operation_and_then_restarts_counting():
    cfg = Config(signal="browse", browse_chain_percent=0, browse_break_every_minutes=(60, 60),
                 browse_break_minutes=(2, 15))
    api, clock, eng, plans = _engine(cfg)
    for _ in range(80):  # 80 Durchläufe, je 60 s Abstand
        api.advance(60_000)
        clock.t += 60
        eng.step()
    with_break = [i for i, p in enumerate(plans) if _breaks(p)]
    assert len(with_break) == 1 and 55 <= with_break[0] <= 65, with_break
    secs = _breaks(plans[with_break[0]])[0][1]
    assert 120 <= secs <= 900


def test_user_activity_resets_long_operation():
    cfg = Config(signal="browse", browse_chain_percent=0, browse_break_every_minutes=(10, 10))
    api, clock, eng, plans = _engine(cfg)
    for i in range(30):
        api.advance(60_000)
        clock.t += 60
        eng.step()
        if i % 5 == 4:
            api.advance(2_000)
            api.last = api.now  # Sie sind kurz da
            api.advance(1_000)
            eng.step()
    assert not any(_breaks(p) for p in plans)


def test_breaks_can_be_switched_off():
    cfg = Config(signal="browse", browse_chain_percent=0, browse_breaks=False, browse_break_every_minutes=(10, 10))
    api, clock, eng, plans = _engine(cfg)
    for _ in range(40):
        api.advance(60_000)
        clock.t += 60
        eng.step()
    assert plans and not any(_breaks(p) for p in plans)


def test_sessions_sometimes_follow_without_gap():
    cfg = Config(signal="browse", interval_seconds=60, browse_chain_percent=20, browse_breaks=False)
    api, clock, eng, plans = _engine(cfg)
    chained = 0
    for _ in range(400):
        api.advance(60_000)
        t = eng.step()
        if t < 10:
            chained += 1
            n = len(plans)
            api.advance(int(t * 1000))
            eng.step()  # Abstand nicht abgelaufen, trotzdem sofort die nächste Sitzung
            assert len(plans) == n + 1
    assert 0.12 < chained / 400 < 0.32, chained


def test_chained_session_waits_if_you_came_back():
    cfg = Config(signal="browse", browse_chain_percent=100, browse_breaks=False)
    api, clock, eng, plans = _engine(cfg)
    api.advance(60_000)
    t = eng.step()
    assert t < 10 and len(plans) == 1
    api.advance(1_000)
    api.last = api.now  # Sie sind da
    eng.step()
    assert len(plans) == 1


# ---------- Tab-Limit nur für eigene Tabs ----------

class TabDesk(FakeDesk):
    """Browser mit echter Tableiste (Tab-IDs, ausgewählter Tab) wie per UI Automation gelesen."""

    def __init__(self, foreign_after=None, foreign_count=1, **kw):
        super().__init__(**kw)
        self.tid = 0
        self.closed = []
        self.foreign = set()
        self.foreign_after = foreign_after
        self.foreign_count = foreign_count
        self.foreign_hits = []

    def _new_tid(self):
        self.tid += 1
        return self.tid

    def _open(self, private=False, title="Neuer Tab", proc="msedge.exe"):
        h = super()._open(private, title, proc)
        self.wins[h].update(tablist=[self._new_tid()], sel=0)
        return h

    def tabs(self, h):
        w = self.wins.get(h)
        if not w or "tablist" not in w:
            return None
        return [(t, i == w["sel"]) for i, t in enumerate(w["tablist"])]

    def _foreign_in_front(self, h):
        w = self.wins.get(h, {})
        return "tablist" in w and w["tablist"][w["sel"]] in self.foreign

    def inject(self, h):
        w = self.wins[h]
        for _ in range(self.foreign_count):
            t = self._new_tid()
            self.foreign.add(t)
            w["tablist"].append(t)
        w["sel"] = len(w["tablist"]) - 1
        w["tabs"] = len(w["tablist"])

    def type_char(self, ch):
        if self._foreign_in_front(self.foreground()):
            self.foreign_hits.append(("type", ch))
        super().type_char(ch)

    def click(self, ctrl=False):
        h = self.foreground()
        if self._foreign_in_front(h):
            self.foreign_hits.append(("click", ctrl))
        w = self.wins.get(h, {})
        if ctrl and "tablist" in w:
            self._input()
            w["tablist"].insert(w["sel"] + 1, self._new_tid())
            w["tabs"] = len(w["tablist"])
            return
        super().click(ctrl)

    def send_combo(self, vks):
        name = "+".join(NAMES[v] for v in vks)
        h = self.foreground()
        w = self.wins.get(h)
        if w is None or "tablist" not in w:
            return super().send_combo(vks)
        if self._foreign_in_front(h) and name not in SWITCH and name != "ctrl+n":
            self.foreign_hits.append(("key", name))
        tl, i = w["tablist"], w["sel"]
        if name in ("ctrl+t", "ctrl+shift+k", "ctrl+u"):
            self._input()
            self.sent.append((h, name))
            tl.insert(i + 1, self._new_tid())
            w["sel"] = i + 1
        elif name in ("ctrl+w", "ctrl+f4"):
            self._input()
            self.sent.append((h, name))
            self.closed.append(tl.pop(i))
            if not tl:
                self._close(h)
                return
            w["sel"] = min(i, len(tl) - 1)
        elif name in NEXT or name in PREV:
            self._input()
            self.sent.append((h, name))
            w["sel"] = (i + (1 if name in NEXT else -1)) % len(tl)
        elif name in SWITCH:
            self._input()
            self.sent.append((h, name))
            n = int(name[-1])
            w["sel"] = len(tl) - 1 if n == 9 else min(n, len(tl)) - 1
        else:
            super().send_combo(vks)
        if h in self.wins:
            w["tabs"] = len(tl)
        own = [x for x in self.wins if x != USER and "tablist" in self.wins[x]]
        mid_typing = name == "back"  # Rücktaste mitten im Tippen: ein Tab kommt zwischen zwei Schritten
        if self.foreign_after is not None and len(self.sent) >= self.foreign_after and own and not mid_typing:
            self.foreign_after = None
            self.inject(own[0])


def test_foreign_tab_in_test_window_is_never_closed_or_used():
    seen = kept = 0
    for seed in range(60):
        desk = TabDesk(foreign_after=8 + seed % 15)
        _, res = _run(desk, seed, cfg=Config(signal="browse", browse_actions_max=40))
        assert res.status in ("done", "aborted"), (seed, res)
        assert not desk.foreign & set(desk.closed), seed
        assert desk.foreign_hits == [], (seed, desk.foreign_hits[:5])
        assert desk.wins[USER]["tabs"] == 3 and [k for h, k in desk.sent if h == USER] == ["ctrl+n"]
        if desk.foreign:
            seen += 1
            rest = [w for h, w in desk.wins.items() if h != USER]
            if res.status == "done":
                kept += 1
                assert all(set(w["tablist"]) <= desk.foreign for w in rest)  # eigene zu, fremde bleiben
    assert seen > 40 and kept > 20


def test_tab_limit_counts_only_own_tabs():
    peaks = []
    for seed in range(40):
        desk = TabDesk(foreign_after=4, foreign_count=6)
        cfg = Config(signal="browse", browse_actions_max=80)
        plan = make_scenario(cfg, random.Random(seed))
        runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(seed))
        peak = 0
        orig = desk.send_combo

        def watch(vks, orig=orig):
            nonlocal peak
            orig(vks)
            for h, w in desk.wins.items():
                if "tablist" in w:
                    peak = max(peak, sum(t not in desk.foreign for t in w["tablist"]))
        desk.send_combo = watch
        res = runner.run(plan, ())
        assert res.status in ("done", "aborted"), (seed, res)
        assert not desk.foreign & set(desk.closed)
        assert peak <= MAX_TABS + 1, (seed, peak)  # 6 fremde Tabs blockieren die eigenen nicht
        peaks.append(peak)
    assert max(peaks) >= 4


def test_without_foreign_tabs_tracking_closes_everything_as_before():
    for seed in range(30):
        desk = TabDesk()
        _, res = _run(desk, seed, cfg=Config(signal="browse", browse_actions_max=30))
        assert res.status == "done", (seed, res)
        assert set(desk.wins) == {USER}


def test_unstable_tab_ids_fall_back_to_plan_counting():
    for seed in range(20):
        desk = TabDesk()
        orig = desk.tabs
        desk.tabs = lambda h: [(t + desk.ms * 1000, s) for t, s in orig(h)] if orig(h) else None  # IDs wechseln
        _, res = _run(desk, seed, cfg=Config(signal="browse", browse_actions_max=30))
        assert res.status == "done", (seed, res)
        assert set(desk.wins) == {USER}


def test_default_break_spacing_is_mostly_1_to_2_hours_but_sometimes_up_to_4():
    cfg = Config(signal="browse")
    dues = []
    for seed in range(2000):
        api, clock, eng = make(cfg, rng=random.Random(seed))
        eng._break_due(cfg)
        dues.append(eng._op_due / 3600)
    assert min(dues) >= 1 and max(dues) <= 4
    early = sum(d <= 2 for d in dues) / len(dues)
    late = sum(d >= 3 for d in dues) / len(dues)
    assert 0.45 < early < 0.65 and 0.05 < late < 0.2, (early, late)
