import time

from awaketoggle.config import Config
from awaketoggle.core import LOCKED, SEND, TEXT_INEFFECTIVE, TEXT_LOCKED, TEXT_USER, USER_ACTIVE, WAIT, Engine, decide


class FakeApi:
    def __init__(self):
        self.now = 1_000_000
        self.last = 1_000_000
        self.locked = False
        self.effective = True
        self.sent = []
        self.awake = []

    def tick(self):
        return self.now & 0xFFFFFFFF

    def last_input_tick(self):
        return self.last & 0xFFFFFFFF

    def set_awake(self, on):
        self.awake.append(on)
        return True

    def is_locked(self):
        return self.locked

    def execute(self, plan):
        self.sent.append(plan.label)
        if self.effective:
            self.last = self.now
        return True

    def advance(self, ms):
        self.now += ms


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def make(cfg=None, rng=None):
    api, clock = FakeApi(), Clock()
    return api, clock, Engine(api, cfg or Config(), clock=clock, sleep=lambda s: None, rng=rng)


def test_decide_basic_and_wraparound():
    assert decide(70_000, 10_000, None, 60_000, False) == (SEND, 0)
    assert decide(30_000, 10_000, None, 60_000, False) == (USER_ACTIVE, 40_000)
    assert decide(30_000, 10_000, 10_000, 60_000, False) == (WAIT, 40_000)
    assert decide(30_000, 10_100, 10_000, 60_000, False)[0] == WAIT
    assert decide(0, 0, None, 60_000, True)[0] == LOCKED
    assert decide(59_600, 0xFFFFFFFF - 399, None, 60_000, False)[0] == SEND


def test_inactive_does_nothing():
    api, _, eng = make()
    assert eng.step() is None
    assert api.awake == [] and api.sent == []
    assert eng.status.state == "off"


def test_active_pauses_while_user_active_then_sends():
    api, _, eng = make()
    eng.set_active(True)
    api.advance(20_000)
    assert eng.step() == 40.0
    assert api.awake == [True] and api.sent == []
    assert eng.status.text == TEXT_USER
    api.advance(40_000)
    assert eng.step() == 60.0
    assert api.sent == ["Maus"]
    assert eng.status.state == "on" and "letztes Signal" in eng.status.text


def test_own_signal_is_not_mistaken_for_user():
    api, _, eng = make()
    eng.set_active(True)
    api.advance(60_000)
    eng.step()
    api.advance(30_000)
    assert eng.step() == 30.0
    assert len(api.sent) == 1 and eng.status.state == "on"
    api.advance(30_000)
    eng.step()
    assert len(api.sent) == 2


def test_user_input_resets_schedule():
    api, _, eng = make()
    eng.set_active(True)
    api.advance(60_000)
    eng.step()
    api.advance(10_000)
    api.last = api.now
    api.advance(50_000)
    assert eng.step() == 10.0
    assert len(api.sent) == 1 and eng.status.text == TEXT_USER


def test_locked_screen_pauses():
    api, _, eng = make()
    eng.set_active(True)
    api.locked = True
    api.advance(120_000)
    assert eng.step() == 10.0
    assert api.sent == [] and eng.status.state == "paused" and eng.status.text == TEXT_LOCKED
    api.locked = False
    eng.step()
    assert api.sent == ["Maus"]


def test_session_lock_flag_pauses():
    api, _, eng = make()
    eng.set_active(True)
    eng.set_session_locked(True)
    api.advance(120_000)
    eng.step()
    assert api.sent == [] and eng.status.text == TEXT_LOCKED


def test_ineffective_signal_is_reported():
    api, _, eng = make()
    api.effective = False
    eng.set_active(True)
    api.advance(60_000)
    eng.step()
    assert api.sent == ["Maus"] and eng.status.state == "paused" and eng.status.text == TEXT_INEFFECTIVE


def test_f15_signal():
    api, _, eng = make(Config(signal="f15"))
    eng.set_active(True)
    api.advance(60_000)
    eng.step()
    assert api.sent == ["F15"]


def test_timer_switches_off():
    api, clock, eng = make(Config(timer_hours=1))
    events = []
    eng.on_status = events.append
    eng.set_active(True)
    eng.step()
    assert eng.status.deadline is not None
    clock.t = 3599.0
    api.advance(10_000)
    assert eng.step() <= 1.0
    clock.t = 3600.0
    assert eng.step() is None
    assert not eng.active and api.awake == [True, False]
    assert eng.status.reason == "timer" and "Timer abgelaufen" in eng.status.text
    assert any(s.reason == "timer" for s in events)


def test_timer_restarts_on_config_change():
    _, clock, eng = make(Config(timer_hours=1))
    eng.set_active(True)
    clock.t = 1000.0
    eng.update_config(Config(timer_hours=4))
    assert eng._deadline == 1000.0 + 4 * 3600


def test_deactivate_releases_awake():
    api, _, eng = make()
    eng.set_active(True)
    eng.step()
    eng.set_active(False)
    eng.step()
    assert api.awake == [True, False]


def test_thread_shutdown_releases_awake():
    api, _, eng = make()
    eng.start()
    eng.set_active(True)
    for _ in range(200):
        if api.awake:
            break
        time.sleep(0.01)
    eng.shutdown()
    assert api.awake == [True, False]
    assert not eng._thread.is_alive()
    eng.shutdown()
    assert api.awake == [True, False]


def test_shutdown_without_thread_is_safe():
    api, _, eng = make()
    eng.shutdown()
    eng.set_active(True)
    assert not eng.active and api.awake == []


def test_run_now_forces_signal_even_if_user_active():
    api, clock, eng = make(Config(interval_seconds=60))
    eng.run_now()
    assert eng.active
    eng.step()
    assert len(api.sent) == 1
    eng.step()
    assert len(api.sent) == 1
