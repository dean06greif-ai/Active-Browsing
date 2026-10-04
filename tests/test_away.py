from awaketoggle.away import Away
from awaketoggle.browse_runner import Result
from awaketoggle.config import Config
from awaketoggle.core import Engine
from tests.test_core import Clock, FakeApi


class FakePower:
    def __init__(self):
        self.calls = []

    def dim(self, cfg):
        self.calls.append(("dim", cfg.away_brightness, cfg.away_energy_saver))

    def restore(self, cfg):
        self.calls.append(("restore", cfg.back_brightness))


def make(cfg=None):
    api, power = FakeApi(), FakePower()
    away = Away(power, api, poll_s=0.01)
    away._start_watcher = lambda: None
    eng = Engine(api, cfg or Config(signal="browse"), clock=Clock(), sleep=lambda s: None, away=away)
    return api, power, away, eng


def test_away_dims_on_run_and_restores_when_user_returns():
    api, power, away, eng = make()
    pokes = []
    away.on_back = lambda: pokes.append(1)

    def browse(plan, cfg, cancel):
        assert away.active and power.calls == [("dim", 0, True)]
        api.advance(5_000)
        api.last = api.now
        return Result("done", "ok")
    api.browse = browse
    eng.set_active(True)
    api.advance(60_000)
    eng.step()
    assert away.active
    api.advance(1_000)
    assert away.check() is False
    api.advance(2_000)
    api.last = api.now
    assert away.check() is True and not away.active
    assert power.calls == [("dim", 0, True), ("restore", 50)] and pokes == [1]


def test_away_stays_on_between_runs_and_only_dims_once():
    api, power, away, eng = make()

    def browse(plan, cfg, cancel):
        api.advance(3_000)
        api.last = api.now
        return Result("done", "ok")
    api.browse = browse
    eng.set_active(True)
    for _ in range(3):
        api.advance(61_000)
        eng.step()
        assert away.check() is False
    assert power.calls == [("dim", 0, True)] and away.active


def test_away_leaves_when_run_aborted_by_user_and_when_switched_off():
    api, power, away, eng = make()
    api.browse = lambda plan, cfg, cancel: Result("aborted", "Sie sind aktiv")
    eng.set_active(True)
    api.advance(60_000)
    eng.step()
    assert not away.active and power.calls == [("dim", 0, True), ("restore", 50)]

    api.browse = lambda plan, cfg, cancel: Result("aborted", "Fokus nicht im eigenen Testfenster")
    api.advance(60_000)
    eng.step()
    assert away.active
    eng.set_active(False)
    eng.step()
    assert not away.active and power.calls[-1] == ("restore", 50)


def test_away_disabled_never_touches_power_and_custom_levels():
    api, power, away, eng = make(Config(signal="browse", away_power=False))
    api.browse = lambda plan, cfg, cancel: Result("done", "ok")
    eng.set_active(True)
    api.advance(60_000)
    eng.step()
    assert power.calls == []

    api, power, away, eng = make(Config(signal="mouse", away_brightness=10, back_brightness=70,
                                        away_energy_saver=False))
    eng.set_active(True)
    api.advance(60_000)
    eng.step()
    assert power.calls == [("dim", 10, False)]
    api.advance(5_000)
    api.last = api.now
    eng.step()
    assert power.calls[-1] == ("restore", 70) and not away.active


def test_away_restored_on_shutdown():
    api, power, away, eng = make(Config(signal="mouse"))
    eng.set_active(True)
    api.advance(60_000)
    eng.step()
    assert away.active
    eng.shutdown()
    assert not away.active and power.calls[-1] == ("restore", 50)


def test_config_away_keys(tmp_path):
    import json
    from awaketoggle.config import load
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"away_power": False, "away_brightness": 5, "back_brightness": 80}), "utf-8")
    cfg, warnings = load(p)
    assert warnings == [] and (cfg.away_power, cfg.away_brightness, cfg.back_brightness) == (False, 5, 80)
    p.write_text(json.dumps({"away_brightness": 150, "back_brightness": "x", "away_energy_saver": 1}), "utf-8")
    cfg, warnings = load(p)
    assert len(warnings) == 3 and cfg == Config()
