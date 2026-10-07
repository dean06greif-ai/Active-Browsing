"""v1.9.0: Zähler ablesen aus / nach jeder Sitzung / zufällig, nur einmal am Sitzungsende, Verlauf mit Sitzungsdaten."""
import json
import random
from datetime import datetime

from awaketoggle.browse import make_scenario
from awaketoggle.browse_runner import Result, Runner
from awaketoggle.config import Config, load
from awaketoggle.history import HEADER, CoinHistory
from awaketoggle.tray_labels import badge_mode_label
from tests.test_browse import FakeDesk


def _clock(start=datetime(2026, 6, 10, 12, 0)):
    t = [start]

    def now():
        cur = t[0]
        t[0] = cur.replace(minute=cur.minute + 10) if cur.minute < 50 else cur.replace(hour=cur.hour + 1, minute=0)
        return cur
    return now


def test_want_off_session_random():
    h = CoinHistory("/nonexistent/x.csv", rng=random.Random(3))
    assert not any(h.want(Config(badge_mode="off")) for _ in range(50))
    assert all(h.want(Config(badge_mode="session")) for _ in range(50))
    hits = sum(h.want(Config(badge_mode="random", badge_random_percent=25)) for _ in range(4000))
    assert 850 < hits < 1150


def test_session_done_counts_sessions_and_stores_session_data(tmp_path):
    h = CoinHistory(tmp_path / "c.csv", now=_clock())
    cfg = Config(badge_mode="random", badge_random_percent=25)
    h.session_done(Result("aborted", "Sie sind aktiv"), cfg)
    h.session_done(Result("done", "x", 12, seconds=80.4), cfg)
    h.session_done(Result("done", "x", 9, seconds=60.0), cfg)
    assert h.sessions == 2 and h.records() == []
    h.session_done(Result("done", "x", 22, seconds=181.6, badge=480, badge_read=True), cfg)
    h.session_done(Result("done", "x", 7, seconds=50.0, badge=487, badge_read=True), cfg)
    h.session_done(Result("done", "x", 7, seconds=50.0, badge=None, badge_read=True), cfg)
    assert h.sessions == 0
    r = h.records()
    assert r[0] == ["2026-06-10 12:00:00", "480", "0", "", "3", "20", "182", "zufällig ca. 25 %", "erste Messung",
                    "Mittwoch"]
    assert r[1][:9] == ["2026-06-10 12:10:00", "487", "7", "10.0", "1", "5", "50", "zufällig ca. 25 %", "gestiegen"]
    assert r[2][1] == "" and r[2][8] == "nicht lesbar" and r[2][3] == "10.0"
    assert h.last == 487


def test_not_increased_status(tmp_path):
    h = CoinHistory(tmp_path / "c.csv", now=_clock())
    h.record(487)
    h.record(487)
    assert h.records()[1][8] == "nicht gestiegen"


def test_old_three_column_csv_is_migrated(tmp_path):
    p = tmp_path / "power_coins.csv"
    p.write_text("Zeit;Wert;Änderung\n2026-06-10 11:00:00;470;0\n2026-06-10 11:30:00;480;10\n", "utf-8-sig")
    h = CoinHistory(p, now=_clock())
    assert h.last == 480
    assert p.read_text("utf-8-sig").splitlines()[0] == ";".join(HEADER)
    h.record(487)
    assert h.records()[-1][3] == "30.0"
    assert h.rows() == [("2026-06-10 11:00:00", 470, 0), ("2026-06-10 11:30:00", 480, 10),
                        ("2026-06-10 12:00:00", 487, 7)]
    CoinHistory(p)
    assert len(p.read_text("utf-8-sig").splitlines()) == 4


def test_html_shows_all_columns_and_rate(tmp_path):
    h = CoinHistory(tmp_path / "c.csv", now=_clock())
    for v in (480, 485, 490):
        h.record(v)
    page = h.html_path.read_text("utf-8")
    assert "Sitzungen seit letzter Messung" in page and "Wochentag" in page
    assert "<b>+30.0</b>" in page  # 10 Coins in 20 Minuten = 30 pro Stunde


def test_runner_reads_only_once_at_end_never_at_start():
    desk = FakeDesk()
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(2))
    plan = make_scenario(Config(browse_actions_max=10), random.Random(2))
    seen = []
    orig = r._check

    def check(kind="key"):
        seen.append("step")
        orig(kind)
    r._check = check
    res = r.run(plan, (), badge=lambda h: seen.append("badge") or 500, badge_prev=490)
    assert res.status == "done" and seen.count("badge") == 1 and seen[-1] == "badge"
    assert res.actions == len(plan.steps) and res.badge == 500 and res.badge_read
    assert "Zähler 490 → 500" in res.text


def test_runner_without_badge_does_not_read():
    desk = FakeDesk()
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(2))
    res = r.run(make_scenario(Config(browse_actions_max=3), random.Random(2)), (), badge=None, badge_prev=490)
    assert res.status == "done" and not res.badge_read and res.badge is None and "Zähler" not in res.text
    assert res.seconds > 0


def test_runner_skips_reading_when_user_became_active():
    desk = FakeDesk()
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(2))
    r._cancel = lambda: True
    assert r._badge_after_session(lambda h: 1 / 0, 1) == (False, None)


def test_runner_unreadable_counter_is_a_problem():
    desk = FakeDesk()
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(2))
    res = r.run(make_scenario(Config(browse_actions_max=3), random.Random(2)), (), badge=lambda h: None)
    assert res.badge_read and res.badge is None
    assert "Zähler konnte nicht gelesen werden" in res.problems


def test_config_badge_mode_and_old_badge_read(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"badge_read": False}), "utf-8")
    cfg, warnings = load(p)
    assert cfg.badge_mode == "off" and warnings == []
    p.write_text(json.dumps({"badge_read": True}), "utf-8")
    assert load(p)[0].badge_mode == "session"
    p.write_text(json.dumps({"badge_mode": "random", "badge_random_percent": 40}), "utf-8")
    cfg, warnings = load(p)
    assert (cfg.badge_mode, cfg.badge_random_percent, warnings) == ("random", 40, [])
    p.write_text(json.dumps({"badge_mode": "oft", "badge_random_percent": 0}), "utf-8")
    cfg, warnings = load(p)
    assert (cfg.badge_mode, cfg.badge_random_percent, len(warnings)) == ("session", 25, 2)


def test_badge_mode_labels():
    assert badge_mode_label("off") == "Aus (nie ablesen)"
    assert badge_mode_label("session") == "Nach jeder Sitzung"
    assert badge_mode_label("random", 25) == "Zufällig ab und zu (ca. 25 % der Sitzungen)"
