"""Weg-Modus: solange der Test für Sie arbeitet, Bildschirm dunkel + Stromsparen; sobald Sie zurück sind, wieder hell.

Plattformunabhängig; die eigentlichen Windows-Aufrufe stecken in `power` (siehe power_win.Power).
"""
import logging
import threading

log = logging.getLogger(__name__)

MASK = 0xFFFFFFFF
OWN_SLACK_MS = 300
POLL_S = 0.3


class Away:
    def __init__(self, power, api, on_back=None, poll_s: float = POLL_S):
        self._power = power
        self._api = api
        self.on_back = on_back
        self._poll_s = poll_s
        self._lock = threading.RLock()
        self._on = False
        self._busy = False
        self._mark = None
        self._mark_tick = 0
        self._cfg = None
        self._thread = None

    @property
    def active(self) -> bool:
        return self._on

    def enter(self, cfg) -> None:
        """Vor jedem Signal/Durchlauf: eigene Eingaben folgen, also nicht als Rückkehr werten."""
        with self._lock:
            self._busy, self._cfg = True, cfg
            if self._on:
                return
            self._on = True
        log.info("Weg-Modus an: Helligkeit %d %%%s", cfg.away_brightness,
                 ", Stromsparmodus an" if cfg.away_energy_saver else "")
        try:
            self._power.dim(cfg)
        except Exception:
            log.exception("Weg-Modus: Helligkeit/Stromsparen konnte nicht gesetzt werden")
        self._start_watcher()

    def done(self) -> None:
        """Nach jedem Signal/Durchlauf: ab jetzt zählt jede neue Eingabe als „Sie sind zurück“."""
        with self._lock:
            self._mark = self._api.last_input_tick()
            self._mark_tick = self._api.tick()
            self._busy = False

    def leave(self, reason: str) -> None:
        with self._lock:
            if not self._on:
                return
            self._on, self._busy, cfg = False, False, self._cfg
        log.info("Weg-Modus aus (%s): Helligkeit %d %%%s", reason, cfg.back_brightness,
                 ", Stromsparmodus aus" if cfg.away_energy_saver else "")
        try:
            self._power.restore(cfg)
        except Exception:
            log.exception("Weg-Modus: Helligkeit/Stromsparen konnte nicht zurückgesetzt werden")

    def check(self) -> bool:
        """Eine Prüfung des Wächters; True, wenn Sie zurück sind (dann ist der Weg-Modus schon aus)."""
        with self._lock:
            if not self._on or self._busy or self._mark is None:
                return False
            last = self._api.last_input_tick()
            if last == self._mark:
                return False
            if ((last - self._mark_tick) & MASK) <= OWN_SLACK_MS:
                self._mark = last
                return False
        self.leave("Sie sind zurück")
        if self.on_back:
            self.on_back()
        return True

    def _start_watcher(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._watch, name="AwayWatcher", daemon=True)
        self._thread.start()

    def _watch(self) -> None:
        stop = threading.Event()
        while self._on:
            try:
                self.check()
            except Exception:
                log.exception("Weg-Modus: Prüfung fehlgeschlagen")
            stop.wait(self._poll_s)
