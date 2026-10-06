import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from . import APP_NAME
from .browse import ACTION_IDS, REMOVED_IDS

log = logging.getLogger(__name__)

SIGNALS = ("mouse", "f15", "random", "browse")
VARIANTS = ("mouse", "scroll", "keys")
JITTER_CHOICES = (0, 10, 25, 50)
INTERVAL_CHOICES = (5, 10, 15, 30, 60, 120, 300)
TIMER_CHOICES = (0, 1, 4, 8)
BROWSE_LENGTH_CHOICES = (10, 20, 40)
BROWSE_ACTIONS_MIN, BROWSE_ACTIONS_MAX = 3, 100
BREAK_MINUTES_RANGE = (1, 120)
BREAK_EVERY_RANGE = (10, 600)
CHAIN_CHOICES = (0, 10, 20, 40)
INTERVAL_MIN, INTERVAL_MAX = 1, 3600
TIMER_MAX_HOURS = 24
DEFAULT_UPDATE_REPO = "dean06greif-ai/Active-Browsing"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class Config:
    interval_seconds: int = 60
    signal: str = "mouse"
    timer_hours: float = 0
    start_active: bool = False
    verbose_log: bool = False
    random_variants: tuple = VARIANTS
    jitter_percent: int = 0
    browse_processes: tuple = ()
    browse_actions_max: int = 20
    browse_exclude: tuple = ()
    browse_private_words: tuple = ()
    browse_accept_cookies: bool = True
    browse_breaks: bool = True
    browse_break_minutes: tuple = (2, 15)
    browse_break_every_minutes: tuple = (60, 240)
    browse_chain_percent: int = 20
    badge_read: bool = True
    badge_popup: bool = True
    badge_extension: str = ""
    away_power: bool = True
    away_brightness: int = 0
    back_brightness: int = 50
    away_energy_saver: bool = True
    update_repo: str = DEFAULT_UPDATE_REPO


def app_dir() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / APP_NAME


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _num(v):
    return int(v) if float(v).is_integer() else float(v)


def validate(raw: dict) -> tuple[Config, list[str]]:
    d = Config()
    warnings = []
    values = {}

    iv = raw.get("interval_seconds", d.interval_seconds)
    if not _is_number(iv) or not INTERVAL_MIN <= iv <= INTERVAL_MAX:
        warnings.append(f"interval_seconds={iv!r} ungültig ({INTERVAL_MIN}–{INTERVAL_MAX}), nutze {d.interval_seconds}")
        iv = d.interval_seconds
    values["interval_seconds"] = int(iv)

    sig = raw.get("signal", d.signal)
    if sig not in SIGNALS:
        warnings.append(f"signal={sig!r} ungültig (mouse, f15, random oder browse), nutze {d.signal}")
        sig = d.signal
    values["signal"] = sig

    th = raw.get("timer_hours", d.timer_hours)
    if not _is_number(th) or not 0 <= th <= TIMER_MAX_HOURS:
        warnings.append(f"timer_hours={th!r} ungültig (0–{TIMER_MAX_HOURS}, 0 = unbegrenzt), nutze 0")
        th = d.timer_hours
    values["timer_hours"] = _num(th)

    for key in ("start_active", "verbose_log", "badge_read", "badge_popup", "away_power", "away_energy_saver",
                "browse_accept_cookies", "browse_breaks"):
        v = raw.get(key, getattr(d, key))
        if not isinstance(v, bool):
            warnings.append(f"{key}={v!r} ungültig (true oder false), nutze {getattr(d, key)}")
            v = getattr(d, key)
        values[key] = v

    rv = raw.get("random_variants", list(d.random_variants))
    if not isinstance(rv, list) or not rv or any(v not in VARIANTS for v in rv):
        warnings.append(f"random_variants={rv!r} ungültig (Liste aus {', '.join(VARIANTS)}), nutze alle")
        rv = d.random_variants
    values["random_variants"] = tuple(dict.fromkeys(rv))

    jp = raw.get("jitter_percent", d.jitter_percent)
    if not _is_number(jp) or not 0 <= jp <= 50:
        warnings.append(f"jitter_percent={jp!r} ungültig (0–50), nutze 0")
        jp = d.jitter_percent
    values["jitter_percent"] = int(jp)

    bp = raw.get("browse_processes", list(d.browse_processes))
    if not isinstance(bp, list) or any(not isinstance(v, str) or not v.strip() for v in bp):
        warnings.append(f"browse_processes={bp!r} ungültig (Liste von Programmnamen wie powerbrowser.exe), nutze []")
        bp = d.browse_processes
    values["browse_processes"] = tuple(dict.fromkeys(v.strip().lower() for v in bp))

    ba = raw.get("browse_actions_max", d.browse_actions_max)
    if not _is_number(ba) or not BROWSE_ACTIONS_MIN <= ba <= BROWSE_ACTIONS_MAX:
        warnings.append(f"browse_actions_max={ba!r} ungültig ({BROWSE_ACTIONS_MIN}–{BROWSE_ACTIONS_MAX}), "
                        f"nutze {d.browse_actions_max}")
        ba = d.browse_actions_max
    values["browse_actions_max"] = int(ba)

    be = raw.get("browse_exclude", list(d.browse_exclude))
    if isinstance(be, list):
        be = [v for v in be if v not in REMOVED_IDS]
    if not isinstance(be, list) or any(v not in ACTION_IDS for v in be):
        warnings.append(f"browse_exclude={be!r} ungültig (Liste aus {', '.join(ACTION_IDS)}), nutze []")
        be = d.browse_exclude
    values["browse_exclude"] = tuple(dict.fromkeys(be))

    for key, (lo, hi) in (("browse_break_minutes", BREAK_MINUTES_RANGE),
                          ("browse_break_every_minutes", BREAK_EVERY_RANGE)):
        v = raw.get(key, list(getattr(d, key)))
        if not (isinstance(v, list) and len(v) == 2 and all(_is_number(x) for x in v) and lo <= v[0] <= v[1] <= hi):
            warnings.append(f"{key}={v!r} ungültig ([von, bis] mit {lo} ≤ von ≤ bis ≤ {hi}), "
                            f"nutze {list(getattr(d, key))}")
            v = getattr(d, key)
        values[key] = tuple(_num(x) for x in v)

    cp = raw.get("browse_chain_percent", d.browse_chain_percent)
    if not _is_number(cp) or not 0 <= cp <= 100:
        warnings.append(f"browse_chain_percent={cp!r} ungültig (0–100), nutze {d.browse_chain_percent}")
        cp = d.browse_chain_percent
    values["browse_chain_percent"] = int(cp)

    pw = raw.get("browse_private_words", list(d.browse_private_words))
    if not isinstance(pw, list) or any(not isinstance(v, str) or not v.strip() for v in pw):
        warnings.append(f"browse_private_words={pw!r} ungültig (Liste von Titelwörtern wie \"privat-tab\"), nutze []")
        pw = d.browse_private_words
    values["browse_private_words"] = tuple(dict.fromkeys(v.strip().lower() for v in pw))

    bx = raw.get("badge_extension", d.badge_extension)
    if not isinstance(bx, str):
        warnings.append(f"badge_extension={bx!r} ungültig (Teil des Erweiterungsnamens oder \"\"), nutze \"\"")
        bx = d.badge_extension
    values["badge_extension"] = bx.strip()

    for key in ("away_brightness", "back_brightness"):
        v = raw.get(key, getattr(d, key))
        if not _is_number(v) or not 0 <= v <= 100:
            warnings.append(f"{key}={v!r} ungültig (0–100 %), nutze {getattr(d, key)}")
            v = getattr(d, key)
        values[key] = int(v)

    ur = raw.get("update_repo", d.update_repo)
    if not isinstance(ur, str) or not REPO_RE.match(ur.strip()):
        warnings.append(f"update_repo={ur!r} ungültig (Besitzer/Repository, z. B. \"{d.update_repo}\"), "
                        f"nutze {d.update_repo}")
        ur = d.update_repo
    values["update_repo"] = ur.strip()

    unknown = sorted(set(raw) - set(values))
    if unknown:
        warnings.append(f"Unbekannte Schlüssel ignoriert: {', '.join(unknown)}")
    return Config(**values), warnings


def save(cfg: Config, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(cfg), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load(path: Path) -> tuple[Config, list[str]]:
    if not path.exists():
        cfg = Config()
        save(cfg, path)
        return cfg, []
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict):
            raise ValueError("kein JSON-Objekt")
    except (ValueError, OSError) as e:
        backup = path.with_name("config.invalid.json")
        os.replace(path, backup)
        cfg = Config()
        save(cfg, path)
        return cfg, [f"config.json unlesbar ({e}), Standardwerte aktiv, alte Datei als {backup.name} gesichert"]
    return validate(raw)
