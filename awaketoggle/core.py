import logging
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from .browse import make_scenario
from .config import Config
from .variants import make_plan, next_interval

log = logging.getLogger(__name__)

SEND, WAIT, USER_ACTIVE, LOCKED = "send", "wait", "user_active", "locked"
TICK_MASK = 0xFFFFFFFF
TOLERANCE_MS = 500
OWN_SLACK_MS = 250
LOCK_POLL_S = 10.0
MIN_WAIT_S = 1.0
CONFIRM_TRIES = 5
CONFIRM_DELAY_S = 0.02

TEXT_LOCKED = "Pausiert, Bildschirm gesperrt"
TEXT_INEFFECTIVE = "Pausiert, Signal ohne Wirkung (gesperrt/RDP minimiert?)"
TEXT_USER = "An, Sie sind gerade selbst aktiv"


@dataclass(frozen=True)
class Status:
    state: str  # off | on | paused
    text: str
    deadline: datetime | None = None
    reason: str = ""


def _diff(a: int, b: int) -> int:
    return (a - b) & TICK_MASK


def decide(now: int, last_input: int, own_input: int | None, interval_ms: int, locked: bool) -> tuple[str, int]:
    """Entscheidet über das nächste Signal; liefert (Aktion, Restwartezeit in ms)."""
    if locked:
        return LOCKED, 0
    idle = _diff(now, last_input)
    if idle + TOLERANCE_MS >= interval_ms:
        return SEND, 0
    remaining = interval_ms - idle
    if own_input is not None and _diff(last_input, own_input) <= OWN_SLACK_MS:
        return WAIT, remaining
    return USER_ACTIVE, remaining


class Engine:
    def __init__(self, api, cfg: Config, on_status=None, clock=time.monotonic, sleep=time.sleep, rng=None):
        self._api = api
        self._cfg = cfg
        self.on_status = on_status
        self._clock = clock
        self._sleep = sleep
        self._rng = rng or random.Random()
        self._target_s = None
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._thread = None
        self._quit = False
        self._active = False
        self._applied = False
        self._deadline = None
        self._off_reason = ""
        self._session_locked = False
        self._own_input = None
        self._status = Status("off", "Aus")

    @property
    def active(self) -> bool:
        return self._active

    @property
    def config(self) -> Config:
        return self._cfg

    @property
    def status(self) -> Status:
        return self._status

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="AwakeWorker", daemon=True)
        self._thread.start()

    def _new_deadline(self):
        hours = self._cfg.timer_hours
        return self._clock() + hours * 3600 if hours else None

    def set_active(self, on: bool, reason: str = "") -> None:
        with self._lock:
            if self._quit:
                return
            self._active = on
            self._deadline = self._new_deadline() if on else None
            self._off_reason = "" if on else reason
            self._target_s = None
        log.info("%s%s", "Eingeschaltet" if on else "Ausgeschaltet", f" ({reason})" if reason else "")
        self._wake.set()

    def toggle(self) -> None:
        self.set_active(not self._active)

    def update_config(self, cfg: Config) -> None:
        with self._lock:
            timer_changed = cfg.timer_hours != self._cfg.timer_hours
            self._cfg = cfg
            self._target_s = None
            if self._active and timer_changed:
                self._deadline = self._new_deadline()
        self._wake.set()

    def set_session_locked(self, locked: bool) -> None:
        if locked != self._session_locked:
            log.info("Sitzung %s", "gesperrt/getrennt" if locked else "entsperrt/verbunden")
        self._session_locked = locked
        self._wake.set()

    def poke(self) -> None:
        self._wake.set()

    def shutdown(self, timeout: float = 3.0) -> None:
        with self._lock:
            self._quit = True
        self._wake.set()
        t = self._thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout)
        if not (t and t.is_alive()):
            self._release()

    def _run(self) -> None:
        try:
            while not self._quit:
                try:
                    timeout = self.step()
                except Exception:
                    log.exception("Fehler im Hintergrund-Thread, nächster Versuch nach Abstand")
                    timeout = float(self._cfg.interval_seconds)
                self._wake.wait(timeout)
                self._wake.clear()
        finally:
            self._active = False
            self._release()
            self._publish(Status("off", "Beendet"))

    def _release(self) -> None:
        if self._applied:
            self._api.set_awake(False)
            self._applied = False
            log.info("Wachhalten aufgehoben")

    def _apply(self, on: bool) -> None:
        ok = self._api.set_awake(on)
        self._applied = on
        if on:
            log.info("Wachhalten aktiv%s", "" if ok else " (SetThreadExecutionState fehlgeschlagen)")
        else:
            log.info("Wachhalten aufgehoben")

    def _publish(self, status: Status) -> None:
        if status == self._status:
            return
        self._status = status
        if self.on_status:
            self.on_status(status)

    def step(self) -> float | None:
        """Ein Durchlauf; liefert Sekunden bis zum nächsten Durchlauf (None = bis zum Aufwecken)."""
        with self._lock:
            active, cfg, deadline = self._active, self._cfg, self._deadline
        now = self._clock()
        if active and deadline is not None and now >= deadline:
            with self._lock:
                self._active, self._deadline, self._off_reason = False, None, "Timer abgelaufen"
            log.info("Timer abgelaufen, schalte aus")
            active = False
        if active != self._applied:
            self._apply(active)
        if not active:
            self._own_input = None
            reason = self._off_reason
            self._publish(Status("off", f"Aus ({reason})" if reason else "Aus",
                                 reason="timer" if reason == "Timer abgelaufen" else ""))
            return None
        dl = None
        if deadline is not None:
            dl = (datetime.now() + timedelta(seconds=deadline - now)).replace(second=0, microsecond=0)
        timeout = self._tick(cfg, dl)
        if deadline is not None:
            timeout = min(timeout, max(deadline - now, 0.0))
        return timeout

    def _tick(self, cfg: Config, dl) -> float:
        api = self._api
        if self._target_s is None:
            self._target_s = next_interval(cfg, self._rng)
        target = self._target_s
        locked = self._session_locked or api.is_locked()
        last = api.last_input_tick()
        action, remaining_ms = decide(api.tick(), last, self._own_input, int(target * 1000), locked)

        if action == LOCKED:
            if self._status.text != TEXT_LOCKED:
                log.info("Bildschirm gesperrt, sende keine Signale")
            self._own_input = None
            self._publish(Status("paused", TEXT_LOCKED, dl))
            return min(target, LOCK_POLL_S)

        wait_s = max(remaining_ms / 1000, MIN_WAIT_S)
        if action == USER_ACTIVE:
            self._publish(Status("on", TEXT_USER, dl))
            return wait_s
        if action == WAIT:
            if self._status.state != "on":
                self._publish(Status("on", "An", dl))
            return wait_s

        if cfg.signal == "browse":
            return self._browse(cfg, dl)
        plan = make_plan(cfg, self._rng)
        ok = api.execute(plan)
        after = last
        if ok:
            for _ in range(CONFIRM_TRIES):
                after = api.last_input_tick()
                if after != last:
                    break
                self._sleep(CONFIRM_DELAY_S)
        if ok and after != last:
            self._sleep(CONFIRM_DELAY_S)
            self._own_input = api.last_input_tick()
            stamp = datetime.now().strftime("%H:%M:%S")
            log.log(logging.INFO if cfg.verbose_log else logging.DEBUG, "Signal gesendet (%s, %d Schritte)",
                    plan.label, len(plan.steps))
            self._publish(Status("on", f"An, letztes Signal {stamp} ({plan.label})", dl))
        else:
            self._own_input = None
            if self._status.text != TEXT_INEFFECTIVE:
                log.warning("Signal (%s) ohne Wirkung: SendInput=%s, Leerlaufzähler unverändert", plan.label, ok)
            self._publish(Status("paused", TEXT_INEFFECTIVE, dl))
        self._target_s = next_interval(cfg, self._rng)
        return self._target_s

    def _browse(self, cfg: Config, dl) -> float:
        plan = make_scenario(cfg, self._rng)
        log.info("Starte %s", plan.label)
        result = self._api.browse(plan, cfg, cancel=lambda: self._quit or not self._active)
        stamp = datetime.now().strftime("%H:%M:%S")
        if result.status == "done":
            self._own_input = self._api.last_input_tick()
            log.info("Browser-Test fertig: %s", result.text)
            for p in result.problems:
                log.info("  Auffälligkeit: %s", p)
            self._publish(Status("on", f"An, Browser-Test {stamp}: {result.text}", dl))
        elif result.status == "aborted":
            self._own_input = None
            self._publish(Status("on", f"An, Browser-Test {stamp} abgebrochen ({result.text})", dl))
        else:
            self._own_input = None
            if self._status.text != f"Pausiert, {result.text}":
                log.info("Browser-Test übersprungen: %s", result.text)
            self._publish(Status("paused", f"Pausiert, {result.text}", dl))
        self._target_s = next_interval(cfg, self._rng)
        return self._target_s
