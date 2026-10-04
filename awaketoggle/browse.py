"""Browser-Test: zufällige, aber zustandsbewusste Abfolgen aus Suchen, Tabs, Fenstern, Scrollen und Klicks.

Alles passiert in eigenen, neu geöffneten normalen Fenstern (nie Inkognito/InPrivate); am Ende werden sie geschlossen.
"""
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

STYLES = {  # Wartezeit-Faktor, Tippabstand, Rate verbesserter Vertipper
    "ruhig": (1.6, (0.10, 0.28), 0.02),
    "normal": (1.0, (0.06, 0.18), 0.04),
    "hektisch": (0.55, (0.03, 0.10), 0.07),
}


def combo(text: str) -> tuple:
    if text in BLOCKED:
        raise ValueError(f"Tastenkürzel {text} ist gesperrt")
    return tuple(VK[p] for p in text.split("+"))


@dataclass
class Win:
    tabs: int = 1
    history: int = 0
    loaded: bool = False


@dataclass
class Model:
    wins: list = field(default_factory=list)
    last_query: str = ""

    @property
    def w(self) -> Win:
        return self.wins[-1]


class Builder:
    def __init__(self, rng: random.Random, style: str):
        self.rng = rng
        self.speed, self.type_range, self.slip = STYLES[style]
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

    def type(self, text: str):
        out, delays = [], []
        lo, hi = self.type_range
        for ch in text:
            if ch.isalpha() and self.rng.random() < self.slip:
                out += [queries.neighbor(ch, self.rng), "\b"]
                delays += [self.rng.uniform(lo, hi), self.rng.uniform(hi, hi * 2.5)]
            out.append(ch)
            delays.append(self.rng.uniform(lo, hi) * (2.5 if ch == " " and self.rng.random() < 0.2 else 1))
        self.steps.append(("type", "".join(out), tuple(round(d, 3) for d in delays)))

    def point(self, fx=(0.05, 0.9), fy=(0.05, 0.9)):
        self.steps.append(("point", round(self.rng.uniform(*fx), 3), round(self.rng.uniform(*fy), 3)))

    def wheel(self, delta: int):
        self.steps.append(("wheel", delta))

    def click(self):
        self.steps.append(("click", LOAD_TIMEOUT_S))

    def new_window(self, c: str):
        combo(c)
        self.steps.append(("new_window", c))

    def close_window(self):
        self.steps.append(("close_window",))

    def take(self) -> tuple:
        steps, self.steps = tuple(self.steps), []
        return steps


# ---------- Aktionen: (Gewicht abhängig vom Zustand, Aufbau der Schritte) ----------

def _search(b, m, rng):
    b.key(rng.choice(("ctrl+e", "ctrl+k", "alt+d", "ctrl+l", "f4")))
    b.wait(0.3, 0.9)
    q = queries.make_query(rng)
    if rng.random() < 0.25 and len(q) > 4:
        b.type(q[:rng.randint(2, len(q) - 1)])
        b.wait(0.8, 2.0)
        b.key("down", rng.randint(1, 3))
        b.wait(0.3, 0.8)
        label = f"Vorschlag zu '{q}'"
    else:
        b.type(q)
        b.wait(0.2, 0.8)
        label = f"Suche '{q}'"
    b.nav("enter", label)
    b.wait(1.0, 3.0)
    m.w.loaded, m.last_query = True, q
    m.w.history += 1


def _search_cancel(b, m, rng):
    b.key(rng.choice(("ctrl+l", "alt+d", "f4")))
    q = queries.make_query(rng)
    b.type(q[:max(2, len(q) // 2)])
    b.wait(0.6, 2.0)
    b.key("esc", 2)


def _www_com(b, m, rng):
    b.key("ctrl+l")
    b.wait(0.2, 0.6)
    word = rng.choice(queries.SAFE_DOMAINS)
    b.type(word)
    b.nav("ctrl+enter", f"www.{word}.com")
    b.wait(1.5, 4.0)
    m.w.loaded = True
    m.w.history += 1


def _new_tab(b, m, rng):
    b.key("ctrl+t")
    b.wait(0.5, 1.5)
    m.w.tabs += 1
    m.w.loaded = False


def _close_tab(b, m, rng):
    b.key("ctrl+w")
    b.wait(0.5, 1.5)
    m.w.tabs -= 1
    m.w.loaded = m.w.history > 0


def _duplicate_tab(b, m, rng):
    b.key("ctrl+shift+k")
    b.wait(1.0, 2.5)
    m.w.tabs += 1


def _switch_tab(b, m, rng):
    n = m.w.tabs
    options = ["ctrl+tab", "ctrl+shift+tab", "ctrl+pgdn", "ctrl+pgup", "ctrl+9"]
    options += [f"ctrl+{i}" for i in range(1, min(n, 8) + 1)]
    for i in range(rng.randint(1, 3)):
        if i:
            b.wait(0.4, 1.5)
        b.key(rng.choice(options))
    b.wait(0.8, 2.5)
    m.w.loaded = m.w.history > 0


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
    b.wait(1.0, 3.0)
    if rng.random() < 0.6:
        b.key("alt+right")
        b.wait(1.0, 3.0)


def _home(b, m, rng):
    b.key("alt+home")
    b.wait(1.5, 3.5)
    m.w.loaded = True
    m.w.history += 1


def _reload(b, m, rng):
    b.key(rng.choice(("f5", "ctrl+r", "shift+f5")))
    if rng.random() < 0.25:
        b.wait(0.1, 0.4)
        b.key("esc")
    b.wait(1.0, 3.0)


def _read_scroll(b, m, rng):
    b.point()
    b.wait(0.2, 0.6)
    down = 1 if rng.random() < 0.75 else -1
    for _ in range(rng.randint(2, 8)):
        b.wheel(-down * 120 * rng.randint(1, 3))
        b.wait(0.4, 2.5)
        if rng.random() < 0.2:
            down = -down


def _key_scroll(b, m, rng):
    b.key("ctrl+f6")
    b.wait(0.3, 0.8)
    pool = ("space", "space", "pgdn", "pgdn", "shift+space", "pgup", "end", "home")
    for _ in range(rng.randint(2, 6)):
        b.key(rng.choice(pool))
        b.wait(0.6, 2.2)


def _click(b, m, rng):
    b.point((0.05, 0.6), (0.1, 0.8))
    b.wait(0.3, 1.0)
    b.click()
    b.wait(1.0, 3.0)
    m.w.history += 1


def _find(b, m, rng):
    b.key(rng.choice(("ctrl+f", "f3")))
    b.wait(0.3, 0.8)
    b.type(queries.find_word(rng, m.last_query))
    b.wait(0.4, 1.2)
    for _ in range(rng.randint(1, 4)):
        b.key(rng.choice(("enter", "ctrl+g", "f3")))
        b.wait(0.3, 1.0)
    if rng.random() < 0.6:
        b.key("ctrl+shift+g")
        b.wait(0.3, 1.0)
    b.key("esc")


def _zoom(b, m, rng):
    b.key("ctrl+add", rng.randint(1, 3))
    b.wait(0.8, 2.0)
    b.key("ctrl+subtract", rng.randint(1, 4))
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
    for _ in range(rng.randint(2, 6)):
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
    b.wait(2.0, 10.0)


ACTIONS = {
    "suche": (lambda m: 6.0 if not m.w.loaded else 2.5, _search),
    "suche_abbrechen": (lambda m: 0.4, _search_cancel),
    "www_com": (lambda m: 0.5, _www_com),
    "neuer_tab": (lambda m: 2.0 if m.w.tabs < MAX_TABS else 0, _new_tab),
    "tab_schliessen": (lambda m: 0.4 + (m.w.tabs - 2) * 0.7 if m.w.tabs > 1 else 0, _close_tab),
    "tab_duplizieren": (lambda m: 0.6 if m.w.loaded and m.w.tabs < MAX_TABS else 0, _duplicate_tab),
    "tab_wechseln": (lambda m: 1.6 if m.w.tabs > 1 else 0, _switch_tab),
    "neues_fenster": (lambda m: 0.4 if len(m.wins) < MAX_WINDOWS else 0, _new_window),
    "fenster_schliessen": (lambda m: 0.4 + m.w.tabs * 0.1 if len(m.wins) > 1 else 0, _close_window),
    "zurueck_vor": (lambda m: 1.0 if m.w.history >= 2 else 0, _back_forward),
    "startseite": (lambda m: 0.25, _home),
    "neu_laden": (lambda m: 0.8 if m.w.loaded else 0, _reload),
    "lesen_scrollen": (lambda m: 3.0 if m.w.loaded else 0, _read_scroll),
    "tastatur_scrollen": (lambda m: 1.2 if m.w.loaded else 0, _key_scroll),
    "klicken": (lambda m: 1.6 if m.w.loaded else 0, _click),
    "auf_seite_suchen": (lambda m: 1.0 if m.w.loaded else 0, _find),
    "zoom": (lambda m: 0.6 if m.w.loaded else 0, _zoom),
    "vollbild": (lambda m: 0.3, _fullscreen),
    "reader": (lambda m: 0.3 if m.w.loaded else 0, _toggle_twice("f9", 2.0, 6.0)),
    "caret_browsing": (lambda m: 0.15, _open_then_esc("f7", 0.8, 1.5)),
    "verlauf": (lambda m: 0.4, _open_then_esc("ctrl+h")),
    "downloads": (lambda m: 0.3, _open_then_esc("ctrl+j")),
    "favoriten": (lambda m: 0.3, _open_then_esc("ctrl+shift+o")),
    "sammlungen": (lambda m: 0.2, _toggle_twice("ctrl+shift+y", 1.0, 3.0)),
    "seitenleiste_suche": (lambda m: 0.2, _open_then_esc("ctrl+shift+e")),
    "favoritenleiste": (lambda m: 0.2, _toggle_twice("ctrl+shift+b", 1.0, 2.5)),
    "favoritenleiste_fokus": (lambda m: 0.2, _favbar_focus),
    "quelltext": (lambda m: 0.35 if m.w.loaded else 0, _view_source),
    "stumm": (lambda m: 0.2, _toggle_twice("ctrl+m", 1.0, 3.0)),
    "vorlesen": (lambda m: 0.25 if m.w.loaded else 0, _toggle_twice("ctrl+shift+u", 3.0, 8.0)),
    "fokus_bereiche": (lambda m: 0.6, _focus_cycle),
    "menue": (lambda m: 0.3, _menu),
    "kontextmenue": (lambda m: 0.3, _context_menu),
    "pdf": (lambda m: 0.12 if m.w.loaded else 0, _pdf),
    "pause": (lambda m: 1.2, _pause),
}
ACTION_IDS = tuple(ACTIONS)
REMOVED_IDS = frozenset({"inprivate_fenster", "tab_wiederherstellen"})  # alte config.json bleibt gültig


def make_scenario(cfg, rng: random.Random) -> Plan:
    exclude = set(cfg.browse_exclude)
    style = rng.choice(tuple(STYLES))
    b, m = Builder(rng, style), Model()
    _new_window(b, m)
    actions = [("start (neues Fenster)", b.take())]
    n = rng.randint(max(3, cfg.browse_actions_max // 3), cfg.browse_actions_max)
    last = None
    for _ in range(n):
        ids, weights = [], []
        for aid, (weight, _) in ACTIONS.items():
            w = weight(m) if aid not in exclude else 0
            if w > 0:
                ids.append(aid)
                weights.append(w * (0.25 if aid == last else 1.0))
        aid = rng.choices(ids, weights)[0] if ids else "pause"
        ACTIONS[aid][1](b, m, rng)
        actions.append((aid, b.take()))
        last = aid
    while m.wins:
        _close_window(b, m, rng)
    actions.append(("aufräumen", b.take()))
    return Plan("browse", tuple(actions), f"Browser-Test ({style}, {n} Aktionen)")
