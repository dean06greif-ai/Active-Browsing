"""Browser-Test: Abläufe, die sich wie ein Mensch verhalten – mit Anliegen, Gewohnheiten und Lesepausen.

Ein Durchlauf ist eine kleine Surf-Sitzung: ein oder mehrere Anliegen (z. B. „Wetter fürs Wochenende“),
suchen, Ergebnis anklicken, lesen, zurück, nächstes Ergebnis, Suche verfeinern, Tabs für Nebenthemen.
Jede Sitzung hat eine Person mit festen Gewohnheiten (bevorzugtes Tastenkürzel, Tempo, Neugier).
Selten genutzte Browserfunktionen kommen nur gelegentlich und höchstens einmal je Durchlauf vor.
Alles passiert in eigenen, neu geöffneten normalen Fenstern (nie Inkognito/InPrivate); am Ende werden sie geschlossen.
"""
import math
import random
from dataclasses import dataclass, field

from . import queries
from .variants import Plan

KNOWN_BROWSERS = frozenset({
    "msedge.exe", "chrome.exe", "brave.exe", "vivaldi.exe", "opera.exe", "chromium.exe", "thorium.exe",
    "browser.exe", "arc.exe",
    "power.exe", "powerbrowser.exe", "power browser.exe", "power-browser.exe", "power_browser.exe", "powerbrowser64.exe",
})


class BrowserNames:
    """Erkennt Browser: bekannte Programme, eigene Einträge und alles mit „browser“/„power“ im Namen (außer PowerShell)."""

    def __init__(self, extra=()):
        self.extra = frozenset(n.lower() for n in extra)

    def __contains__(self, name) -> bool:
        name = (name or "").lower()
        return name in self.extra or name in KNOWN_BROWSERS or "browser" in name or \
            (name.startswith("power") and not name.startswith(("powershell", "powertoys", "powercfg")))

PRIVATE_WORDS = (
    "inprivate", "incognito", "inkognito", "private browsing", "privates surfen", "privater modus",
    "privates fenster", "private window", "privatmodus", "privat-modus",
)


def is_private(title: str, extra=()) -> bool:
    """Inkognito-/InPrivate-Fenster am Fenstertitel erkennen (eigene Wörter über browse_private_words)."""
    t = (title or "").lower()
    return any(w in t for w in PRIVATE_WORDS) or any(w and w in t for w in extra)


MAX_TABS = 6
MAX_WINDOWS = 2
LOAD_TIMEOUT_S = 15.0

BLOCKED = frozenset({
    "alt+f4", "ctrl+shift+w", "ctrl+shift+delete", "ctrl+p", "ctrl+s", "ctrl+o", "f12",
    "ctrl+shift+i", "ctrl+shift+p", "alt+shift+i", "ctrl+d", "ctrl+shift+d", "ctrl+shift+v", "ctrl+shift+l",
    "ctrl+shift+n",  # Inkognito/InPrivate
    "ctrl+shift+t",  # stellt browserweit den zuletzt geschlossenen Tab wieder her, evtl. einen fremden
    "ctrl+shift+a",  # Tab-Suche springt auch in fremde Fenster
})

VK = {
    "ctrl": 0x11, "shift": 0x10, "alt": 0x12, "back": 0x08, "tab": 0x09, "enter": 0x0D, "esc": 0x1B,
    "space": 0x20, "pgup": 0x21, "pgdn": 0x22, "end": 0x23, "home": 0x24, "left": 0x25, "up": 0x26,
    "right": 0x27, "down": 0x28, "delete": 0x2E, "add": 0x6B, "subtract": 0x6D,
    "oem4": 0xDB, "oem5": 0xDC, "oem6": 0xDD,
    **{str(i): 0x30 + i for i in range(10)},
    **{chr(c): c - 32 for c in range(ord("a"), ord("z") + 1)},
    **{f"f{i}": 0x6F + i for i in range(1, 13)},
}


STYLES = {  # Wartezeit-Faktor, mittlerer Tippabstand (s), Rate bemerkter Vertipper
    "ruhig": (1.5, 0.21, 0.012),
    "normal": (1.0, 0.14, 0.022),
    "hektisch": (0.6, 0.09, 0.04),
}
SEARCH_KEYS = ("ctrl+l", "ctrl+e", "alt+d", "ctrl+k", "f4")
TAB_KEYS = ("ctrl+tab", "ctrl+pgdn", "ctrl+shift+tab", "ctrl+pgup")


def combo(text: str) -> tuple:
    if text in BLOCKED:
        raise ValueError(f"Tastenkürzel {text} ist gesperrt")
    return tuple(VK[p] for p in text.split("+"))


@dataclass
class Win:
    tabs: int = 1
    history: int = 0
    page: str = "leer"  # leer | ergebnisse | seite
    unread: int = 0

    @property
    def loaded(self) -> bool:
        return self.page != "leer"


@dataclass
class Person:
    """Gewohnheiten für einen Durchlauf: Menschen benutzen immer wieder dieselben Wege."""
    search_key: str
    tab_key: str
    curiosity: float  # Neigung, Ergebnisse in neuen Tabs zu öffnen
    reader: float  # Lesedauer-Faktor

    @classmethod
    def random(cls, rng):
        return cls(search_key=rng.choices(SEARCH_KEYS, (5, 2, 2, 1, 0.5))[0],
                   tab_key=rng.choices(TAB_KEYS, (5, 2, 1, 0.5))[0],
                   curiosity=rng.uniform(0.1, 0.6), reader=rng.lognormvariate(0, 0.35))

    def pick(self, rng, habit, options, loyal=0.85):
        return habit if rng.random() < loyal else rng.choice(options)


@dataclass
class Model:
    wins: list = field(default_factory=list)
    last_query: str = ""
    interest: object = None
    person: Person = None
    used: set = field(default_factory=set)
    unread_searches: int = 0  # Suchen hintereinander, ohne etwas gelesen zu haben

    @property
    def w(self) -> Win:
        return self.wins[-1]


class Builder:
    def __init__(self, rng: random.Random, style: str):
        self.rng = rng
        self.speed, self.type_mid, self.slip = STYLES[style]
        self.steps = []

    def key(self, c: str, times: int = 1, gap=(0.15, 0.5)):
        combo(c)
        for i in range(times):
            if i:
                self.wait(*gap)
            self.steps.append(("key", c))

    def nav(self, c: str, label: str):
        combo(c)
        self.steps.append(("nav", c, LOAD_TIMEOUT_S, label))

    def wait(self, a: float, b: float):
        self.steps.append(("wait", round(self.rng.uniform(a, b) * self.speed, 2)))

    def dwell(self, median: float, spread: float = 0.5, cap: float = 60.0):
        """Menschliche Pause: meist um den Median, manchmal deutlich länger (log-normal)."""
        s = min(self.rng.lognormvariate(math.log(median), spread), cap) * self.speed
        self.steps.append(("wait", round(max(s, 0.05), 2)))

    def _char_delay(self, ch: str, prev: str) -> float:
        d = self.rng.lognormvariate(math.log(self.type_mid), 0.35)
        if ch == " ":
            d *= self.rng.uniform(1.2, 2.2)
        elif ch.isdigit() or not ch.isascii():
            d *= 1.35
        elif ch == prev:
            d *= 0.7
        if prev == " " and self.rng.random() < 0.08:
            d += self.rng.uniform(0.4, 1.4)  # kurz überlegen
        return d

    def type(self, text: str):
        out, delays, prev, i = [], [], "", 0
        while i < len(text):
            ch = text[i]
            if ch.isalpha() and self.rng.random() < self.slip:
                ahead = text[i + 1:i + 1 + self.rng.randint(0, 2)]
                wrong = queries.neighbor(ch, self.rng) + ahead
                for w in wrong:
                    out.append(w)
                    delays.append(self._char_delay(w, prev))
                    prev = w
                out += ["\b"] * len(wrong)
                delays += [self.rng.uniform(0.35, 0.8)] + [self.rng.uniform(0.07, 0.16) for _ in wrong[1:]]
            out.append(ch)
            delays.append(self._char_delay(ch, prev))
            prev, i = ch, i + 1
        self.steps.append(("type", "".join(out), tuple(round(d, 3) for d in delays)))

    def point(self, fx=(0.05, 0.9), fy=(0.05, 0.9)):
        self.steps.append(("point", round(self.rng.uniform(*fx), 3), round(self.rng.uniform(*fy), 3)))

    def nudge(self):
        self.steps.append(("nudge",))

    def wheel(self, delta: int):
        self.steps.append(("wheel", delta))

    def click(self, ctrl: bool = False):
        self.steps.append(("click", LOAD_TIMEOUT_S, ctrl))

    def new_window(self, c: str):
        combo(c)
        self.steps.append(("new_window", c))

    def close_window(self):
        self.steps.append(("close_window",))

    def take(self) -> tuple:
        steps, self.steps = tuple(self.steps), []
        return steps


# ---------- Bausteine ----------

def _read(b, m, rng, lines=(2, 7)):
    """Lesen: Scroll-Schübe (mehrere kurze Raddrehungen), Lesepausen, mal zurückscrollen, Maus wandert mit."""
    m.unread_searches = 0
    b.point((0.15, 0.7), (0.25, 0.75))
    b.dwell(1.2 * m.person.reader, 0.4)
    for _ in range(rng.randint(*lines)):
        down = 1 if rng.random() < 0.85 else -1
        for _ in range(rng.choices((1, 2, 3, 4), (3, 4, 2, 1))[0]):
            b.wheel(-down * 120)
            b.wait(0.04, 0.16)
        b.dwell(2.2 * m.person.reader, 0.6, cap=25)
        if rng.random() < 0.3:
            b.nudge()


def _type_query(b, m, rng, q):
    b.key(m.person.pick(rng, m.person.search_key, SEARCH_KEYS))
    b.dwell(0.5, 0.4)
    if rng.random() < 0.2 and len(q) > 6:
        b.type(q[:rng.randint(3, len(q) - 2)])
        b.dwell(1.0, 0.4)
        b.key("down", rng.choices((1, 2, 3), (5, 3, 1))[0], gap=(0.3, 0.9))
        b.dwell(0.6, 0.4)
        return f"Vorschlag zu '{q}'"
    b.type(q)
    b.dwell(0.4, 0.5)
    return f"Suche '{q}'"


def _searched(b, m, rng, q, label):
    b.nav("enter", label)
    b.dwell(1.5, 0.4)
    m.w.page, m.last_query = "ergebnisse", q
    m.w.history += 1
    m.unread_searches += 1
    if rng.random() < 0.6:  # Ergebnisliste überfliegen
        b.point((0.1, 0.5), (0.2, 0.7))
        for _ in range(rng.randint(1, 3)):
            b.wheel(-120 * rng.randint(1, 2))
            b.dwell(1.0, 0.5)


# ---------- Aktionen: (Gewicht abhängig vom Zustand, Aufbau der Schritte) ----------

def _search(b, m, rng):
    """Neues Anliegen suchen."""
    m.interest = queries.Interest(rng)
    q = m.interest.first()
    _searched(b, m, rng, q, _type_query(b, m, rng, q))


def _refine(b, m, rng):
    """Suche verfeinern: gleiches Anliegen, genauere oder verwandte Anfrage."""
    q = m.interest.next()
    _searched(b, m, rng, q, _type_query(b, m, rng, q))


def _open_result(b, m, rng):
    """Ergebnis anklicken: Maus zum Treffer, kurz zögern, klicken, lesen, oft wieder zurück zur Liste."""
    b.point((0.05, 0.45), (0.12, 0.65))
    b.dwell(0.7, 0.5)
    if rng.random() < 0.3:
        b.nudge()
        b.dwell(0.4, 0.4)
    b.click()
    b.dwell(1.2, 0.4)
    m.w.page = "seite"
    m.w.history += 1
    _read(b, m, rng)
    if rng.random() < 0.65:
        b.key("alt+left")
        b.dwell(1.5, 0.4)
        m.w.page = "ergebnisse"


def _open_result_tab(b, m, rng):
    """Interessanten Treffer für später im Hintergrund-Tab öffnen (Strg+Klick)."""
    for _ in range(rng.choices((1, 2), (3, 1))[0]):
        if m.w.tabs >= MAX_TABS:
            break
        b.point((0.05, 0.45), (0.12, 0.7))
        b.dwell(0.6, 0.4)
        b.click(ctrl=True)
        b.dwell(0.8, 0.4)
        m.w.tabs += 1
        m.w.unread += 1


def _click_link(b, m, rng):
    """Auf einer Seite einem Link folgen."""
    b.point((0.05, 0.7), (0.1, 0.8))
    b.dwell(0.8, 0.5)
    b.click()
    b.dwell(1.5, 0.4)
    m.w.history += 1
    m.w.page = "seite"


def _read_scroll(b, m, rng):
    _read(b, m, rng)


def _key_scroll(b, m, rng):
    b.key("ctrl+f6")
    b.wait(0.3, 0.8)
    pool = ("space", "space", "pgdn", "pgdn", "down", "down", "shift+space", "pgup", "end", "home")
    for _ in range(rng.randint(2, 5)):
        b.key(rng.choice(pool))
        b.dwell(1.8 * m.person.reader, 0.5)


def _www_com(b, m, rng):
    b.key(m.person.pick(rng, m.person.search_key, ("ctrl+l", "alt+d")) if m.person.search_key != "ctrl+k"
          else "ctrl+l")
    b.wait(0.2, 0.6)
    word = rng.choice(queries.SAFE_DOMAINS)
    b.type(word)
    b.nav("ctrl+enter", f"www.{word}.com")
    b.dwell(2.0, 0.4)
    m.w.page = "seite"
    m.w.history += 1


def _new_tab(b, m, rng):
    """Neuer Tab für ein Nebenthema – meist gleich mit Suche."""
    b.key("ctrl+t")
    b.dwell(0.8, 0.4)
    m.w.tabs += 1
    m.w.page = "leer"
    if rng.random() < 0.8:
        _search(b, m, rng)


def _close_tab(b, m, rng):
    b.key("ctrl+w")
    b.dwell(0.8, 0.4)
    m.w.tabs -= 1
    m.w.unread = min(m.w.unread, m.w.tabs - 1)
    m.w.page = "seite" if m.w.history > 0 else "leer"


def _duplicate_tab(b, m, rng):
    b.key("ctrl+shift+k")
    b.wait(1.0, 2.5)
    m.w.tabs += 1


def _switch_tab(b, m, rng):
    """Zum nächsten Tab wechseln; liegt dort ein vorgemerkter Treffer, wird er gelesen."""
    n = m.w.tabs
    key = m.person.pick(rng, m.person.tab_key, TAB_KEYS + tuple(f"ctrl+{i}" for i in range(1, min(n, 8) + 1)))
    b.key(key)
    b.dwell(1.0, 0.4)
    if m.w.unread:
        m.w.unread -= 1
        m.w.page = "seite"
        m.w.history += 1
        _read(b, m, rng, lines=(2, 5))
    else:
        m.w.page = "seite" if m.w.history > 0 else "leer"


def _new_window(b, m, rng=None):
    b.new_window("ctrl+n")
    b.wait(0.8, 2.0)
    m.wins.append(Win())


def _close_window(b, m, rng):
    b.close_window()
    b.wait(0.6, 1.5)
    m.wins.pop()


def _back_forward(b, m, rng):
    b.key("alt+left")
    b.dwell(1.5, 0.4)
    if rng.random() < 0.3:
        b.key("alt+right")
        b.dwell(1.5, 0.4)


def _home(b, m, rng):
    b.key("alt+home")
    b.dwell(2.0, 0.4)
    m.w.page = "seite"
    m.w.history += 1


def _reload(b, m, rng):
    b.key(rng.choices(("f5", "ctrl+r", "shift+f5"), (6, 2, 1))[0])
    if rng.random() < 0.15:
        b.wait(0.1, 0.4)
        b.key("esc")
    b.dwell(1.5, 0.4)


def _search_cancel(b, m, rng):
    """Angefangen zu tippen, es sich anders überlegt."""
    b.key(m.person.pick(rng, m.person.search_key, SEARCH_KEYS))
    q = queries.make_query(rng)
    b.type(q[:max(2, len(q) // 2)])
    b.dwell(1.2, 0.5)
    b.key("esc", 2)


def _find(b, m, rng):
    b.key(rng.choices(("ctrl+f", "f3"), (5, 1))[0])
    b.wait(0.3, 0.8)
    b.type(queries.find_word(rng, m.last_query))
    b.dwell(0.8, 0.4)
    for _ in range(rng.randint(1, 3)):
        b.key(rng.choices(("enter", "ctrl+g", "f3"), (5, 1, 1))[0])
        b.dwell(0.8, 0.5)
    if rng.random() < 0.3:
        b.key("ctrl+shift+g")
        b.wait(0.3, 1.0)
    b.key("esc")


def _zoom(b, m, rng):
    b.key("ctrl+add", rng.randint(1, 2))
    b.dwell(3.0, 0.5)
    if rng.random() < 0.4:
        b.key("ctrl+subtract", rng.randint(1, 2))
        b.wait(0.8, 2.0)
    b.key("ctrl+0")


def _fullscreen(b, m, rng):
    b.key("f11")
    b.wait(1.5, 4.0)
    if m.w.loaded and rng.random() < 0.5:
        b.point()
        b.wheel(-240)
        b.wait(0.5, 1.5)
    b.key("f11")
    b.wait(0.8, 1.5)


def _toggle_twice(c: str, a: float, z: float):
    def build(b, m, rng):
        b.key(c)
        b.wait(a, z)
        b.key(c)
        b.wait(0.4, 1.0)
    return build


def _open_then_esc(c: str, a: float = 1.0, z: float = 3.0):
    def build(b, m, rng):
        b.key(c)
        b.wait(a, z)
        b.key("esc")
        b.wait(0.3, 0.8)
    return build


def _favbar_focus(b, m, rng):
    b.key("alt+shift+b")
    b.wait(0.5, 1.2)
    b.key(rng.choice(("right", "tab")), rng.randint(0, 3))
    b.wait(0.3, 0.8)
    b.key("esc")
    b.wait(0.3, 0.8)


def _view_source(b, m, rng):
    b.key("ctrl+u")
    b.wait(1.5, 3.5)
    if rng.random() < 0.5:
        b.key("pgdn", rng.randint(1, 3))
        b.wait(0.5, 1.5)
    b.key("ctrl+w")
    b.wait(0.5, 1.2)


def _focus_cycle(b, m, rng):
    pool = ("f6", "shift+f6", "ctrl+f6", "tab", "tab", "shift+tab")
    for _ in range(rng.randint(2, 4)):
        b.key(rng.choice(pool))
        b.wait(0.2, 0.9)
    b.key("esc")


def _menu(b, m, rng):
    b.key(rng.choice(("alt", "f10")))
    b.wait(0.6, 1.5)
    b.key("esc", 2)


def _context_menu(b, m, rng):
    b.point()
    b.key("shift+f10")
    b.wait(0.8, 2.0)
    b.key("esc", 2)


def _pdf(b, m, rng):
    b.key("ctrl+oem5")
    b.wait(0.5, 1.2)
    b.key("ctrl+oem5")
    b.key("ctrl+oem4")
    b.wait(0.5, 1.2)
    b.key("ctrl+oem6")
    b.wait(0.4, 1.0)


def _pause(b, m, rng):
    """Abgelenkt: kurz aufs Handy geschaut, Kaffee geholt …"""
    b.dwell(5.0, 0.8, cap=45)


def _results(m):
    return m.w.page == "ergebnisse"


def _page(m):
    return m.w.page == "seite"


def _can_refine(m):
    return m.interest is not None and not m.interest.exhausted and m.w.loaded and m.unread_searches < 2


ACTIONS = {
    # Kern: so verbringen Menschen fast die ganze Zeit
    "suche": (lambda m: 6.0 if not m.w.loaded else (0.5 if _can_refine(m) else 1.5), _search),
    "suche_verfeinern": (lambda m: (2.2 if _results(m) else 1.0) if _can_refine(m) else 0, _refine),
    "ergebnis_oeffnen": (lambda m: 4.5 if _results(m) else 0, _open_result),
    "im_tab_oeffnen": (lambda m: 2.5 * m.person.curiosity if _results(m) and m.w.tabs < MAX_TABS else 0,
                       _open_result_tab),
    "lesen_scrollen": (lambda m: 2.5 if _page(m) else (0.6 if _results(m) else 0), _read_scroll),
    "klicken": (lambda m: 1.0 if _page(m) else 0, _click_link),
    "zurueck_vor": (lambda m: 1.2 if m.w.history >= 2 and _page(m) else 0, _back_forward),
    "tab_wechseln": (lambda m: (0.4 + 3.0 * m.w.unread) if m.w.tabs > 1 else 0, _switch_tab),
    "neuer_tab": (lambda m: 0.8 if m.w.tabs < MAX_TABS and _page(m) else 0, _new_tab),
    "tab_schliessen": (lambda m: 0.3 + (m.w.tabs - 2) * 0.6 if m.w.tabs > 1 and not m.w.unread else 0, _close_tab),
    "pause": (lambda m: 0.7, _pause),
    "tastatur_scrollen": (lambda m: 0.5 if _page(m) else 0, _key_scroll),
    "auf_seite_suchen": (lambda m: 0.35 if _page(m) else 0, _find),
    "suche_abbrechen": (lambda m: 0.2, _search_cancel),
    "neu_laden": (lambda m: 0.2 if m.w.loaded else 0, _reload),
    "www_com": (lambda m: 0.25, _www_com),
    "neues_fenster": (lambda m: 0.12 if len(m.wins) < MAX_WINDOWS and m.last_query else 0, _new_window),
    "fenster_schliessen": (lambda m: 0.4 + m.w.tabs * 0.1 if len(m.wins) > 1 else 0, _close_window),
    # Selten (höchstens einmal je Durchlauf)
    "zoom": (lambda m: 0.15 if m.w.loaded else 0, _zoom),
    "tab_duplizieren": (lambda m: 0.08 if m.w.loaded and m.w.tabs < MAX_TABS else 0, _duplicate_tab),
    "startseite": (lambda m: 0.08, _home),
    "verlauf": (lambda m: 0.08, _open_then_esc("ctrl+h")),
    "kontextmenue": (lambda m: 0.08, _context_menu),
    "downloads": (lambda m: 0.05, _open_then_esc("ctrl+j")),
    "favoriten": (lambda m: 0.05, _open_then_esc("ctrl+shift+o")),
    "vollbild": (lambda m: 0.05, _fullscreen),
    "reader": (lambda m: 0.05 if _page(m) else 0, _toggle_twice("f9", 2.0, 6.0)),
    "fokus_bereiche": (lambda m: 0.05, _focus_cycle),
    "menue": (lambda m: 0.05, _menu),
    "stumm": (lambda m: 0.03, _toggle_twice("ctrl+m", 1.0, 3.0)),
    "vorlesen": (lambda m: 0.03 if _page(m) else 0, _toggle_twice("ctrl+shift+u", 3.0, 8.0)),
    "sammlungen": (lambda m: 0.03, _toggle_twice("ctrl+shift+y", 1.0, 3.0)),
    "seitenleiste_suche": (lambda m: 0.03, _open_then_esc("ctrl+shift+e")),
    "favoritenleiste": (lambda m: 0.03, _toggle_twice("ctrl+shift+b", 1.0, 2.5)),
    "favoritenleiste_fokus": (lambda m: 0.02, _favbar_focus),
    "quelltext": (lambda m: 0.03 if m.w.loaded else 0, _view_source),
    "caret_browsing": (lambda m: 0.02, _open_then_esc("f7", 0.8, 1.5)),
    "pdf": (lambda m: 0.02 if m.w.loaded else 0, _pdf),
}
RARE = frozenset(list(ACTIONS)[list(ACTIONS).index("zoom"):])
ACTION_IDS = tuple(ACTIONS)
REMOVED_IDS = frozenset({"inprivate_fenster", "tab_wiederherstellen"})  # alte config.json bleibt gültig
MAX_RARE = 2
REPEAT_OK = frozenset({"lesen_scrollen", "ergebnis_oeffnen", "suche_verfeinern", "tab_wechseln"})


def make_scenario(cfg, rng: random.Random) -> Plan:
    exclude = set(cfg.browse_exclude)
    style = rng.choices(tuple(STYLES), (2, 5, 1.5))[0]
    b, m = Builder(rng, style), Model(person=Person.random(rng))
    _new_window(b, m)
    actions = [("start (neues Fenster)", b.take())]
    n = rng.randint(max(3, cfg.browse_actions_max // 3), cfg.browse_actions_max)
    last = None
    for _ in range(n):
        ids, weights = [], []
        for aid, (weight, _) in ACTIONS.items():
            if aid in exclude or (aid in RARE and (not m.last_query or aid in m.used
                                                   or len(m.used & RARE) >= MAX_RARE)):
                continue
            w = weight(m)
            if w > 0:
                ids.append(aid)
                weights.append(w * (1.0 if aid != last else 0.6 if aid in REPEAT_OK else 0.2))
        aid = rng.choices(ids, weights)[0] if ids else "pause"
        ACTIONS[aid][1](b, m, rng)
        m.used.add(aid)
        actions.append((aid, b.take()))
        last = aid
    while m.wins:
        _close_window(b, m, rng)
    actions.append(("aufräumen", b.take()))
    return Plan("browse", tuple(actions), f"Browser-Test ({style}, {n} Aktionen)")
