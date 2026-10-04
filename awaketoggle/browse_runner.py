"""Führt einen Browser-Test-Plan aus: nur in eigenen, normalen Fenstern, Abbruch sobald Sie selbst etwas tun.

Grundsätze:
- Inkognito-/InPrivate-Fenster werden nie benutzt, weder als Ausgangsfenster noch als eigenes Testfenster.
- Fremde Fenster und Tabs bekommen nie Eingaben. Einzige Ausnahme: Strg+N im Ausgangsfenster, um das eigene
  Testfenster zu öffnen (verändert dort nichts).
- Geschlossen wird nur, was der Test selbst geöffnet hat (eigene Fenster und Popups direkt nach eigenen Klicks).
"""
import logging
import random
import time
from dataclasses import dataclass, field

from .badge import compare
from .browse import BrowserNames, combo, is_private

log = logging.getLogger(__name__)

MASK = 0xFFFFFFFF
OWN_SLACK_MS = 400
POLL_S = 0.1
NEW_WINDOW_TIMEOUT_S = 6.0
CLOSE_TRIES = 30
SLOW_LOAD_S = 5.0
TOOLBAR_PX = 150
POPUP_AFTER_CLICK_S = 8.0
PRIVATE_CHECK_S = 0.6
NEW_WINDOW_SETTLE_S = 0.4


@dataclass
class Result:
    status: str  # done | aborted | skipped
    text: str
    actions: int = 0
    problems: list = field(default_factory=list)


class Abort(Exception):
    pass


class Runner:
    def __init__(self, desk, sleep=time.sleep, clock=time.monotonic, rng=None):
        self.desk = desk
        self._sleep = sleep
        self._clock = clock
        self._rng = rng or random.Random()
        self.leftover = []  # [(Fensterhandle, Titel beim Abbruch)]
        self._private_words = ()

    # ---------- Ablauf ----------

    def run(self, plan, processes, cancel=lambda: False, verbose=False, badge=None, private_words=()) -> Result:
        d = self.desk
        self._private_words = tuple(private_words)
        processes = BrowserNames(processes)
        fg = self._bring_browser_to_front(processes)
        if isinstance(fg, Result):
            return fg
        processes = BrowserNames(tuple(processes.extra) + (d.process_name(fg),))
        self._processes, self._cancel, self._base = processes, cancel, fg
        self._problems, self._stack, self._opened = [], [], False
        self._last_click = None
        before = self._read_badge(badge, fg)
        self._mark()
        self._cleanup_leftover()
        self._known = d.top_windows()
        cursor = d.cursor()
        start, done = self._clock(), 0
        level = logging.INFO if verbose else logging.DEBUG
        try:
            for name, steps in plan.steps:
                log.log(level, "Browser-Test: %s", name)
                for step in steps:
                    self._check(step[0])
                    getattr(self, "_do_" + step[0])(*step[1:])
                done += 1
        except Abort as e:
            self.leftover = [(h, d.title(h)) for h in self._stack if d.is_window(h)]
            if self.leftover:
                log.warning("Browser-Test abgebrochen (%s), %d eigene(s) Fenster bleibt offen", e, len(self.leftover))
            else:
                log.info("Browser-Test abgebrochen (%s)", e)
            return Result("aborted", str(e), done, self._problems)
        d.move_to(*cursor)
        self._mark()
        text = f"{max(done - 2, 0)} Aktionen in {self._clock() - start:.0f} s"
        if badge:
            badge_text, issue = compare(before, self._read_badge(badge, fg))
            if issue:
                self._problem(issue)
            if badge_text:
                log.info("Browser-Test %s", badge_text)
                text = f"{badge_text}, {text}"
        if self._problems:
            text += f", {len(self._problems)} Auffälligkeit(en)"
        return Result("done", text, done, self._problems)

    def _is_private(self, h) -> bool:
        return bool(h) and is_private(self.desk.title(h), self._private_words)

    def _read_badge(self, badge, h):
        if not badge:
            return None
        if self.desk.is_window(h) and self.desk.root(self.desk.foreground()) != h:
            self.desk.activate(h)
            self._sleep(0.5)
        value = badge(h)
        self._mark()
        log.info("Zähler gelesen: %s", value if value is not None else "-")
        return value

    def _bring_browser_to_front(self, processes):
        d = self.desk
        fg = d.root(d.foreground())
        proc = d.process_name(fg) if fg else ""
        if fg and proc in processes and not self._is_private(fg):
            return fg
        if fg and proc in processes:
            log.info("Vorne ist ein Inkognito-/InPrivate-Fenster – wird nicht benutzt, suche normales Fenster")
        h = d.find_browser(processes, skip=self._is_private)
        if h and d.process_name(h) not in processes:
            log.info("Kein bekannter Browser, nehme oberstes Fenster: %s", d.process_name(h))
        if not h and fg and proc in processes:
            return Result("skipped", "nur Inkognito-/InPrivate-Fenster offen – die werden nie benutzt, "
                                     "bitte ein normales Browserfenster offen lassen")
        if not h:
            return Result("skipped", f"kein Browserfenster gefunden (vorne: {proc or '-'}) – Programmname in "
                                     "browse_processes eintragen; Inkognito-/InPrivate-Fenster werden nie benutzt")
        if not d.activate(h):
            return Result("skipped", f"Browser ließ sich nicht nach vorne holen (vorne: {proc or '-'})")
        self._sleep(0.5)
        if d.root(d.foreground()) != h:
            return Result("skipped", f"Browser ließ sich nicht nach vorne holen (vorne: {proc or '-'})")
        log.info("Browserfenster (%s) nach vorne geholt, vorher vorne: %s", d.process_name(h), proc or "-")
        return h

    def _cleanup_leftover(self) -> None:
        d = self.desk
        old, self.leftover = self.leftover, []
        closed = False
        for h, title in reversed(old):
            if not d.is_window(h):
                continue
            if d.process_name(h) not in self._processes or d.title(h) != title:
                log.info("Übrig gebliebenes Testfenster wurde inzwischen benutzt – wird nicht angefasst")
                continue
            self._stack = [h]
            try:
                self._close_top()
                closed = True
                log.info("Übrig gebliebenes Testfenster geschlossen")
            except Abort as e:
                log.info("Übrig gebliebenes Testfenster nicht geschlossen (%s)", e)
        self._stack = []
        if closed and d.root(d.foreground()) != self._base:
            d.activate(self._base)

    # ---------- Sicherheit ----------

    def _mark(self) -> None:
        self._sent_tick = self.desk.tick()
        self._own_last = self.desk.last_input_tick()

    def _user_active(self) -> bool:
        last = self.desk.last_input_tick()
        if last == self._own_last:
            return False
        delta = ((last - self._sent_tick + 0x80000000) & MASK) - 0x80000000
        if abs(delta) <= OWN_SLACK_MS:
            self._own_last = last
            return False
        return True

    def _check_input(self) -> None:
        if self._cancel():
            raise Abort("ausgeschaltet")
        if self._user_active():
            raise Abort("Sie sind aktiv")

    def _check(self, kind: str = "key") -> None:
        self._check_input()
        if kind != "wait" and self._opened and not self._stack:
            raise Abort("kein eigenes Testfenster mehr offen")
        self._ensure_focus()

    def _target(self):
        return self._stack[-1] if self._stack else self._base

    def _is_new_browser(self, h) -> bool:
        return bool(h) and h not in self._known and h not in self._stack and \
            self.desk.process_name(h) in self._processes

    def _own_popup(self, h) -> bool:
        recent = self._last_click is not None and self._clock() - self._last_click <= POPUP_AFTER_CLICK_S
        return recent and self._is_new_browser(h)

    def _ensure_focus(self) -> None:
        d = self.desk
        if self._opened and not self._stack:
            return
        for _ in range(3):
            target = self._target()
            fg = d.root(d.foreground())
            if fg == target:
                return
            if self._stack and not d.is_window(target):
                self._stack.pop()
                raise Abort("eigenes Testfenster unerwartet geschlossen")
            if self._stack and self._own_popup(fg):
                self._problem("Seite hat ein Popup-Fenster geöffnet (wird geschlossen)")
                self._stack.append(fg)
                self._close_top()
                continue
            if self._stack and d.activate(target):
                if fg and fg not in self._known and fg not in self._stack:
                    log.info("Fremdes Fenster (%s) kam nach vorne – nicht angefasst, zurück zum Testfenster",
                             d.process_name(fg) or "-")
                    self._known.add(fg)
                self._sleep(0.3)
                continue
            break
        raise Abort("Fokus nicht im eigenen Testfenster")

    def _problem(self, text: str) -> None:
        self._problems.append(text)
        log.warning("Browser-Test Auffälligkeit: %s", text)

    def _wait(self, seconds: float, focus: bool = True) -> None:
        end = self._clock() + seconds
        while True:
            self._check_input()
            if focus:
                self._ensure_focus()
            left = end - self._clock()
            if left <= 0:
                return
            self._sleep(min(POLL_S, left))

    def _await_title(self, before: str, timeout: float):
        t0 = self._clock()
        while self._clock() - t0 < timeout:
            self._wait(0.2)
            if self.desk.title(self._target()) != before:
                return self._clock() - t0
        return None

    # ---------- Schritte ----------

    def _send(self, c: str) -> None:
        if self._opened and not self._stack:
            raise Abort("kein eigenes Testfenster mehr offen")
        self.desk.send_combo(combo(c))
        self._mark()

    def _do_key(self, c):
        self._send(c)

    def _do_wait(self, seconds):
        self._wait(seconds)

    def _do_type(self, text, delays):
        for ch, delay in zip(text, delays):
            if ch == "\b":
                self.desk.send_combo(combo("back"))
            else:
                self.desk.type_char(ch)
            self._mark()
            self._wait(delay)

    def _do_nav(self, c, timeout, label):
        before = self.desk.title(self._target())
        self._send(c)
        took = self._await_title(before, timeout)
        if took is None:
            self._problem(f"Keine Reaktion nach {timeout:.0f} s ({label})")
        elif took > SLOW_LOAD_S:
            self._problem(f"Langsam: {took:.1f} s ({label})")
        else:
            log.debug("Geladen in %.1f s (%s)", took, label)

    def _do_wheel(self, delta):
        self.desk.wheel(delta)
        self._mark()

    def _do_point(self, fx, fy):
        d, h = self.desk, self._target()
        left, top, right, bottom = d.window_rect(h)
        scale = d.dpi(h) / 96
        bar = min(TOOLBAR_PX * scale, (bottom - top) * 0.4)
        x = left + 12 * scale + fx * max(right - left - 40 * scale, 1)
        y = top + bar + fy * max(bottom - top - bar - 12 * scale, 1)
        self._glide(x, y)

    def _do_nudge(self):
        """Maus beim Lesen ein Stück weiterbewegen (bleibt im eigenen Fenster)."""
        d, h = self.desk, self._target()
        left, top, right, bottom = d.window_rect(h)
        x0, y0 = d.cursor()
        x = min(max(x0 + self._rng.uniform(-90, 90), left + 20), right - 20)
        y = min(max(y0 + self._rng.uniform(-60, 60), top + TOOLBAR_PX), bottom - 20)
        self._glide(x, y, overshoot=False)

    def _glide(self, x, y, overshoot=True) -> None:
        """Bogenförmige Bewegung mit Beschleunigen/Abbremsen; manchmal leicht übers Ziel und zurück."""
        if overshoot and self._rng.random() < 0.3:
            ox, oy = x + self._rng.uniform(-14, 14), y + self._rng.uniform(-8, 8)
            self._path(ox, oy, self._rng.randint(12, 26))
            self._sleep(self._rng.uniform(0.05, 0.18))
            self._path(x, y, self._rng.randint(3, 6))
        else:
            self._path(x, y, self._rng.randint(12, 28))

    def _path(self, x, y, n) -> None:
        x0, y0 = self.desk.cursor()
        bend = min(80, max(abs(x - x0), abs(y - y0)) / 3)
        cx = (x0 + x) / 2 + self._rng.uniform(-bend, bend)
        cy = (y0 + y) / 2 + self._rng.uniform(-bend, bend)
        for i in range(1, n + 1):
            t = i / n
            e = t * t * (3 - 2 * t)
            px = (1 - e) ** 2 * x0 + 2 * (1 - e) * e * cx + e * e * x
            py = (1 - e) ** 2 * y0 + 2 * (1 - e) * e * cy + e * e * y
            self.desk.move_to(round(px), round(py))
            self._mark()
            self._sleep(self._rng.uniform(0.006, 0.016))

    def _do_click(self, timeout, ctrl=False):
        before = self.desk.title(self._target())
        self._last_click = self._clock()
        self.desk.click(ctrl)
        self._mark()
        if ctrl:
            return
        took = self._await_title(before, min(timeout, 6.0))
        if took is not None and took > SLOW_LOAD_S:
            self._problem(f"Langsam nach Klick: {took:.1f} s")

    def _do_new_window(self, c):
        d = self.desk
        proc = d.process_name(self._target())
        before = d.top_windows()
        self._send(c)
        t0 = self._clock()
        while self._clock() - t0 < NEW_WINDOW_TIMEOUT_S:
            self._wait(0.15, focus=False)
            fg = d.root(d.foreground())
            if fg in before or not self._is_new_browser(fg) or d.process_name(fg) != proc:
                continue
            self._wait(NEW_WINDOW_SETTLE_S, focus=False)
            fresh = [h for h in d.top_windows() - before
                     if h not in self._stack and d.is_app_window(h) and d.process_name(h) == proc]
            if fresh != [fg] or d.root(d.foreground()) != fg:
                self._known |= set(fresh)
                self._problem(f"{len(fresh)} neue Browserfenster gleichzeitig – unklar, welches das eigene ist")
                raise Abort("eigenes Testfenster nicht eindeutig, nichts angefasst")
            self._stack.append(fg)
            self._opened = True
            self._reject_private(fg)
            return
        self._problem(f"Kein neues Fenster nach {NEW_WINDOW_TIMEOUT_S:.0f} s ({c})")
        raise Abort("neues Fenster nicht erkannt")

    def _reject_private(self, h) -> None:
        self._wait(PRIVATE_CHECK_S, focus=False)
        if not self._is_private(h):
            return
        self._problem("Neues Testfenster ist ein Inkognito-/InPrivate-Fenster (wird sofort geschlossen)")
        self._close_top()
        raise Abort("Inkognito-/InPrivate-Fenster wird nicht benutzt")

    def _do_close_window(self):
        self._close_top()

    def _close_top(self) -> None:
        d, h = self.desk, self._stack[-1]
        for _ in range(CLOSE_TRIES):
            if not d.is_window(h) or not d.is_visible(h):
                break
            self._check_input()
            if d.root(d.foreground()) != h:
                if not d.activate(h):
                    raise Abort("Testfenster lässt sich nicht aktivieren")
                self._sleep(0.3)
                continue
            self._send("ctrl+w")
            self._wait(self._rng.uniform(0.3, 0.6), focus=False)
        else:
            raise Abort("Testfenster ließ sich nicht schließen")
        self._stack.pop()
        self._wait(0.4, focus=False)
