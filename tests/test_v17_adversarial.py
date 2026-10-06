"""Adversarial tests for v17 features: long breaks, chaining and own-tab tracking."""
import random

from awaketoggle.browse import make_scenario
from awaketoggle.browse_runner import Result, Runner
from awaketoggle.config import Config, validate
from tests.test_browse import USER, FakeDesk
from tests.test_core import make
from tests.test_v17 import TabDesk, _breaks, _engine, _run


# ---------- Long break: edge cases ----------

def test_break_aborted_mid_pause_leaves_minimized_leftover_cleaned_next_run():
    """Wenn Sie während der langen Pause zurückkommen, bleiben die minimierten Fenster übrig und
    werden vom nächsten Durchlauf aufgeräumt (activate restauriert und schließt sie)."""
    desk = FakeDesk(user_input_at_ms=1_000_000 + 90_000)
    runner, res = _run(desk, 7, pause_s=600)
    assert res.status == "aborted" and res.text == "Sie sind aktiv"
    leftover = [h for h, _ in runner.leftover]
    assert leftover and all(desk.wins[h].get("min") for h in leftover)

    # Nächster Durchlauf räumt die minimierten eigenen Fenster weg.
    desk.user_input_at = None
    desk.activate(USER)
    res2 = runner.run(make_scenario(Config(signal="browse"), random.Random(99)), ())
    assert res2.status == "done"
    assert set(desk.wins) == {USER}


def test_break_at_top_of_random_range_still_valid():
    """Pause-Zeit am oberen Rand (15 min) führt zu entsprechend langer Wartezeit."""
    desk = FakeDesk()
    t0 = desk.ms
    _, res = _run(desk, 11, pause_s=900)
    assert res.status == "done"
    assert desk.ms - t0 >= 900_000


# ---------- Engine: chain + force interplay ----------

def test_force_overrides_user_active_but_chain_does_not():
    cfg = Config(signal="browse", browse_chain_percent=100, browse_breaks=False)
    api, clock, eng, plans = _engine(cfg)
    # Normale Sitzung → chain gesetzt
    api.advance(60_000)
    t = eng.step()
    assert t < 10 and len(plans) == 1
    # Sie werden aktiv, dann run_now: force muss durchkommen, chain nicht.
    api.advance(1_000)
    api.last = api.now
    eng.run_now()
    eng.step()
    assert len(plans) == 2, "force sollte trotz User-Aktivität senden"


def test_chain_percent_zero_never_chains():
    cfg = Config(signal="browse", browse_chain_percent=0, browse_breaks=False)
    api, clock, eng, plans = _engine(cfg)
    for _ in range(50):
        api.advance(60_000)
        t = eng.step()
        assert t >= 10, "ohne chain_percent darf kein kurzer Rückgabewert kommen"


# ---------- Config: boundary values ----------

def test_config_break_minutes_boundary_values():
    cfg, w = validate({"browse_break_minutes": [1, 120], "browse_break_every_minutes": [10, 600]})
    assert w == []
    assert cfg.browse_break_minutes == (1, 120)
    assert cfg.browse_break_every_minutes == (10, 600)


def test_config_break_minutes_outside_boundaries_rejected():
    cfg, w = validate({"browse_break_minutes": [0, 120]})  # lo<1
    assert len(w) == 1 and cfg.browse_break_minutes == Config().browse_break_minutes

    cfg, w = validate({"browse_break_minutes": [1, 121]})  # hi>120
    assert len(w) == 1 and cfg.browse_break_minutes == Config().browse_break_minutes

    cfg, w = validate({"browse_break_every_minutes": [9, 60]})  # lo<10
    assert len(w) == 1

    cfg, w = validate({"browse_break_every_minutes": [10, 601]})  # hi>600
    assert len(w) == 1


def test_config_chain_percent_boundary():
    cfg, w = validate({"browse_chain_percent": 0})
    assert w == [] and cfg.browse_chain_percent == 0
    cfg, w = validate({"browse_chain_percent": 100})
    assert w == [] and cfg.browse_chain_percent == 100
    cfg, w = validate({"browse_chain_percent": -1})
    assert len(w) == 1 and cfg.browse_chain_percent == Config().browse_chain_percent


# ---------- Own-tab tracking: foreign tab injected at various points ----------

def test_many_foreign_tabs_never_touched():
    """Fremde Tabs in großer Zahl im Testfenster – keiner wird je geschlossen oder bedient."""
    for seed in range(20):
        desk = TabDesk(foreign_after=5, foreign_count=4)
        _, res = _run(desk, seed, cfg=Config(signal="browse", browse_actions_max=50))
        assert res.status in ("done", "aborted"), (seed, res)
        assert not desk.foreign & set(desk.closed)
        assert desk.foreign_hits == []


def test_window_with_only_foreign_tabs_stays_open():
    """Fenster mit ausschließlich fremden Tabs darf nicht geschlossen werden."""
    seen_only_foreign = 0
    for seed in range(50):
        desk = TabDesk(foreign_after=3, foreign_count=2)
        _, res = _run(desk, seed, cfg=Config(signal="browse", browse_actions_max=25))
        # Fenster außer USER, die nur fremde Tabs enthalten, müssen am Leben bleiben
        for h, w in desk.wins.items():
            if h == USER or "tablist" not in w:
                continue
            if all(t in desk.foreign for t in w["tablist"]):
                seen_only_foreign += 1
                assert h in desk.wins  # noch offen
    assert seen_only_foreign >= 1


# ---------- Long break: never scheduled at the extreme ends ----------

def test_long_break_never_first_nor_last_step():
    for seed in range(100):
        plan = make_scenario(Config(signal="browse", browse_actions_max=10),
                             random.Random(seed), pause_s=120)
        idx = _breaks(plan)[0][0]
        assert idx > 0  # nie direkt am Anfang (start-Fensteröffnung)
        assert plan.steps[idx][0] == "lange_pause"
        assert plan.steps[-1][0] == "aufräumen"  # Aufräumen bleibt am Ende


# ---------- break_due state machine ----------

def test_break_due_resets_after_pause_taken():
    """Nach einer Pause startet die Zählung neu – nicht sofort erneut auslösen."""
    cfg = Config(signal="browse", browse_chain_percent=0,
                 browse_break_every_minutes=(10, 10), browse_break_minutes=(2, 2))
    api, clock, eng, plans = _engine(cfg)
    for _ in range(30):
        api.advance(60_000)
        clock.t += 60
        eng.step()
    pauses = [i for i, p in enumerate(plans) if _breaks(p)]
    # Es sollten etwa 2-3 Pausen gewesen sein (alle 10 min + reset), nicht alle Durchläufe
    assert 1 <= len(pauses) <= 4
    # Die Pausen sollen zeitlich nicht direkt aufeinanderfolgen
    if len(pauses) >= 2:
        gaps = [b - a for a, b in zip(pauses, pauses[1:])]
        assert all(g >= 8 for g in gaps), gaps
