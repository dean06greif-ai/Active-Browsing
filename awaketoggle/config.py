import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from . import APP_NAME

log = logging.getLogger(__name__)

SIGNALS = ("mouse", "f15", "random")
VARIANTS = ("mouse", "scroll", "keys")
JITTER_CHOICES = (0, 10, 25, 50)
INTERVAL_CHOICES = (30, 60, 120, 300)
TIMER_CHOICES = (0, 1, 4, 8)
INTERVAL_MIN, INTERVAL_MAX = 10, 3600
TIMER_MAX_HOURS = 24


@dataclass(frozen=True)
class Config:
    interval_seconds: int = 60
    signal: str = "mouse"
    timer_hours: float = 0
    start_active: bool = False
    verbose_log: bool = False
    random_variants: tuple = VARIANTS
    jitter_percent: int = 0


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
        warnings.append(f"signal={sig!r} ungültig (mouse, f15 oder random), nutze {d.signal}")
        sig = d.signal
    values["signal"] = sig

    th = raw.get("timer_hours", d.timer_hours)
    if not _is_number(th) or not 0 <= th <= TIMER_MAX_HOURS:
        warnings.append(f"timer_hours={th!r} ungültig (0–{TIMER_MAX_HOURS}, 0 = unbegrenzt), nutze 0")
        th = d.timer_hours
    values["timer_hours"] = _num(th)

    for key in ("start_active", "verbose_log"):
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
