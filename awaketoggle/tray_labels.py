from . import APP_NAME
from .core import Status


def interval_label(sec) -> str:
    return f"{sec} Sekunden" if sec < 120 or sec % 60 else f"{sec // 60} Minuten"


def timer_label(hours) -> str:
    if not hours:
        return "Nie (unbegrenzt)"
    return f"Nach {hours} Stunde" if hours == 1 else f"Nach {hours} Stunden"


def jitter_label(percent) -> str:
    return "Nein (immer gleich)" if not percent else f"Zufällig bis zu {percent} % kürzer"


def browse_length_label(n) -> str:
    names = {10: "Kurz", 20: "Mittel", 40: "Lang"}
    return f"{names.get(n, 'Eigene')} (bis {n} Aktionen)"


def break_label(cfg) -> str:
    lo, hi = cfg.browse_break_minutes
    a, b = cfg.browse_break_every_minutes
    every = f"{a / 60:g}–{b / 60:g} Std" if a % 30 == 0 and b % 30 == 0 else f"{a}–{b} min"
    return f"Lange Pausen ({lo}–{hi} min, etwa alle {every} Betrieb, Fenster minimiert)"


def chain_label(percent) -> str:
    return "Nie (immer mit Abstand)" if not percent else f"In ca. {percent} % der Fälle"


def tooltip(status: Status) -> str:
    text = f"{APP_NAME}: {status.text}"
    if status.deadline:
        text += f"\nAuto-Aus um {status.deadline:%H:%M}"
    return text[:127]
