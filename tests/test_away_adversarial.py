"""Adversarielle Tests für den Weg-Modus (Away).

Decken Lücken ab:
- check() während busy=True (engine inmitten eines Signals) darf nie als "Rückkehr" werten
- Eingaben innerhalb OWN_SLACK_MS nach done() werden als eigene Nachwirkung ignoriert, aber *verschieben* _mark,
  sodass eine echte spätere Eingabe weiterhin erkannt wird
- leave() ist idempotent (zweiter Aufruf darf power.restore nicht noch einmal auslösen)
- enter() ist idempotent (zweiter Aufruf dim't nicht erneut)
- Nach leave() + erneutem enter() wird dim wieder aufgerufen (nicht "stuck off")
"""
from awaketoggle.away import OWN_SLACK_MS, Away
from awaketoggle.config import Config
from tests.test_away import FakePower
from tests.test_core import FakeApi


def _make(cfg=None):
    api, power = FakeApi(), FakePower()
    away = Away(power, api, poll_s=0.01)
    away._start_watcher = lambda: None  # Watcher-Thread nicht starten
    return api, power, away, cfg or Config(signal="browse")


def test_check_during_busy_never_reports_user_back():
    api, power, away, cfg = _make()
    away.enter(cfg)                 # busy=True, on=True, kein done() aufgerufen
    api.advance(10_000)
    api.last = api.now              # massive "Eingabe" – aber done() fehlt
    assert away.check() is False    # busy -> immer False
    assert away.active
    assert power.calls == [("dim", 0, True)]


def test_own_input_slack_bridges_short_residual_but_detects_real_input_later():
    api, power, away, cfg = _make()
    away.enter(cfg)
    api.advance(5_000)
    api.last = api.now              # eigenes Signal registriert sich
    away.done()                     # Markierung setzen
    # Eingabe 100 ms (< OWN_SLACK_MS=300) nach done(): gilt als eigene Nachwirkung
    api.advance(100)
    api.last = api.now
    assert away.check() is False
    assert away.active
    # Weitere Eingabe 500 ms nach done(): > OWN_SLACK_MS -> Rückkehr erkannt
    api.advance(OWN_SLACK_MS + 200)
    api.last = api.now
    assert away.check() is True
    assert not away.active
    assert power.calls == [("dim", 0, True), ("restore", 50)]


def test_leave_is_idempotent():
    api, power, away, cfg = _make()
    away.enter(cfg)
    away.leave("Test")
    away.leave("Test nochmal")      # zweiter Aufruf -> kein zusätzliches restore
    assert power.calls == [("dim", 0, True), ("restore", 50)]


def test_enter_is_idempotent_but_recovers_after_leave():
    api, power, away, cfg = _make()
    away.enter(cfg)
    away.enter(cfg)                 # zweiter enter: kein zusätzliches dim
    assert power.calls == [("dim", 0, True)]
    away.leave("x")
    away.enter(cfg)                 # nach leave: dim wieder erlaubt
    assert power.calls == [("dim", 0, True), ("restore", 50), ("dim", 0, True)]


def test_check_without_prior_enter_is_safe():
    api, power, away, cfg = _make()
    away.done()                     # done ohne enter: _mark gesetzt, _on=False
    api.advance(5_000)
    api.last = api.now
    assert away.check() is False    # darf nicht crashen und nicht leave auslösen
    assert power.calls == []


def test_on_back_callback_only_fires_when_user_actually_returns():
    api, power, away, cfg = _make()
    fired = []
    away.on_back = lambda: fired.append(1)
    away.enter(cfg)
    api.advance(1_000)
    api.last = api.now
    away.done()
    # Innerhalb Slack: kein Callback
    api.advance(50)
    api.last = api.now
    assert away.check() is False
    assert fired == []
    # Außerhalb Slack: Callback einmal
    api.advance(OWN_SLACK_MS + 500)
    api.last = api.now
    assert away.check() is True
    assert fired == [1]
    # Nach Rückkehr: weitere check-Aufrufe lösen keinen weiteren Callback aus
    api.advance(1_000)
    api.last = api.now
    assert away.check() is False
    assert fired == [1]
