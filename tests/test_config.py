import json

from awaketoggle import autostart
from awaketoggle.config import Config, load, save
from awaketoggle.icons import make_icon, save_ico
from awaketoggle.logsetup import BACKUPS, MAX_BYTES
from awaketoggle.tray_labels import interval_label, timer_label


def test_creates_defaults(tmp_path):
    p = tmp_path / "AwakeToggle" / "config.json"
    cfg, warnings = load(p)
    assert cfg == Config() and warnings == []
    assert json.loads(p.read_text("utf-8")) == {
        "interval_seconds": 60, "signal": "mouse", "timer_hours": 0, "start_active": False, "verbose_log": False,
        "random_variants": ["mouse", "scroll", "keys"], "jitter_percent": 0,
        "browse_processes": [], "browse_actions_max": 20, "browse_exclude": []}


def test_roundtrip(tmp_path):
    p = tmp_path / "config.json"
    cfg = Config(interval_seconds=120, signal="f15", timer_hours=4, start_active=True)
    save(cfg, p)
    assert load(p) == (cfg, [])
    assert '"timer_hours": 4' in p.read_text("utf-8")


def test_invalid_values_fall_back(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"interval_seconds": 2, "signal": "x", "timer_hours": -1,
                             "start_active": "yes", "foo": 1}), "utf-8")
    cfg, warnings = load(p)
    assert cfg == Config()
    assert len(warnings) == 5


def test_bool_is_not_a_number(tmp_path):
    p = tmp_path / "config.json"
    p.write_text('{"interval_seconds": true}', "utf-8")
    cfg, warnings = load(p)
    assert cfg.interval_seconds == 60 and warnings


def test_bom_and_custom_values(tmp_path):
    p = tmp_path / "config.json"
    p.write_bytes(b"\xef\xbb\xbf" + b'{"interval_seconds": 45, "timer_hours": 2.5}')
    cfg, warnings = load(p)
    assert cfg.interval_seconds == 45 and cfg.timer_hours == 2.5 and warnings == []


def test_broken_json_is_backed_up(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{kaputt", "utf-8")
    cfg, warnings = load(p)
    assert cfg == Config() and len(warnings) == 1
    assert (tmp_path / "config.invalid.json").read_text("utf-8") == "{kaputt"
    assert json.loads(p.read_text("utf-8"))["interval_seconds"] == 60


def test_icons(tmp_path):
    for state in ("off", "on", "paused"):
        img = make_icon(state)
        assert img.size == (64, 64) and img.mode == "RGBA"
    assert make_icon("on").getpixel((32, 8))[:3] == (34, 170, 85)
    save_ico(tmp_path / "a.ico")
    assert (tmp_path / "a.ico").stat().st_size > 1000


def test_log_rotation_limit():
    assert MAX_BYTES * (BACKUPS + 1) <= 1024 * 1024


def test_autostart_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert not autostart.is_enabled()
    target, args = autostart.launch_command()
    assert args.endswith('main.py"')
    autostart.shortcut_path().parent.mkdir(parents=True)
    autostart.shortcut_path().write_bytes(b"x")
    assert autostart.is_enabled()
    autostart.disable()
    assert not autostart.is_enabled()


def test_labels():
    assert interval_label(30) == "30 Sekunden"
    assert interval_label(60) == "60 Sekunden"
    assert interval_label(120) == "2 Minuten"
    assert interval_label(90) == "90 Sekunden"
    assert timer_label(0) == "Nie (unbegrenzt)"
    assert timer_label(1) == "Nach 1 Stunde"
    assert timer_label(8) == "Nach 8 Stunden"
