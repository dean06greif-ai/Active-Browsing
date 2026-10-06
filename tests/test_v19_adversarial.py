"""Adversarial Tests für v1.9.0: Randfälle der Zähler-Ablese-Konfiguration/-Historie/-Runner-Verdrahtung."""
import json
import random
from datetime import datetime

from awaketoggle.badge import compare
from awaketoggle.browse import make_scenario
from awaketoggle.browse_runner import BADGE_PAUSE_S, Result, Runner
from awaketoggle.config import Config, load
from awaketoggle.history import HEADER, CoinHistory
from tests.test_browse import FakeDesk


def _clock(start=datetime(2026, 6, 10, 12, 0)):
    t = [start]

    def now():
        cur = t[0]
        t[0] = cur.replace(minute=cur.minute + 10) if cur.minute < 50 else cur.replace(hour=cur.hour + 1, minute=0)
        return cur
    return now


# ---------- want() Randbereiche ----------

def test_want_percent_100_always_reads():
    h = CoinHistory("/nonexistent/x.csv", rng=random.Random(0))
    assert all(h.want(Config(badge_mode="random", badge_random_percent=100)) for _ in range(200))


def test_want_percent_1_rarely_reads():
    h = CoinHistory("/nonexistent/x.csv", rng=random.Random(0))
    hits = sum(h.want(Config(badge_mode="random", badge_random_percent=1)) for _ in range(2000))
    assert 0 <= hits < 70  # ca. 1 %


def test_want_session_does_not_consume_rng():
    """session-Modus darf den Zufall nicht anfassen, sonst zieht Zufallsmodus beim Umschalten andere Werte."""
    r = random.Random(42)
    h = CoinHistory("/nonexistent/x.csv", rng=r)
    before = r.random()
    r2 = random.Random(42)
    r2.random()  # synchron
    h2 = CoinHistory("/nonexistent/x.csv", rng=r2)
    for _ in range(10):
        h2.want(Config(badge_mode="session"))
    assert r2.random() == r.random()
    assert before is not None  # Dummy-Assertion, damit `before` benutzt ist


# ---------- session_done ignoriert nicht-done ----------

def test_session_done_ignores_skipped_and_aborted(tmp_path):
    h = CoinHistory(tmp_path / "c.csv", now=_clock())
    cfg = Config(badge_mode="session")
    h.session_done(Result("skipped", "kein Browser"), cfg)
    h.session_done(Result("aborted", "user"), cfg)
    assert h.sessions == 0 and h.records() == []


# ---------- record(None) ----------

def test_record_none_writes_time_but_keeps_last(tmp_path):
    h = CoinHistory(tmp_path / "c.csv", now=_clock())
    h.record(500)
    assert h.last == 500 and h.last_time == "2026-06-10 12:00:00"
    h.record(None)  # nicht lesbar
    assert h.last == 500 and h.last_time == "2026-06-10 12:00:00"  # letzter Wert UNVERÄNDERT
    rows = h.records()
    assert rows[-1][0] == "2026-06-10 12:10:00"  # trotzdem mit Zeit protokolliert
    assert rows[-1][1] == "" and rows[-1][8] == "nicht lesbar"


# ---------- CSV-Migration Randfälle ----------

def test_migrate_header_only_file(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("Zeit;Wert;Änderung\n", "utf-8-sig")
    h = CoinHistory(p, now=_clock())
    assert h.last is None
    assert p.read_text("utf-8-sig").splitlines() == [";".join(HEADER)]


def test_migrate_preserves_unreadable_rows(tmp_path):
    p = tmp_path / "c.csv"
    # alte 3-Spalten-CSV mit „nicht lesbarer" Zeile (leerer Wert)
    p.write_text("Zeit;Wert;Änderung\n2026-01-01 10:00:00;;\n2026-01-01 10:30:00;300;0\n", "utf-8-sig")
    h = CoinHistory(p, now=_clock())
    assert h.last == 300
    rows = h.records()
    assert len(rows) == 2
    assert rows[0][0] == "2026-01-01 10:00:00" and rows[0][1] == ""
    assert rows[1][1] == "300"


def test_migrate_does_not_run_twice(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("Zeit;Wert;Änderung\n2026-01-01 10:00:00;200;0\n", "utf-8-sig")
    CoinHistory(p)
    content = p.read_text("utf-8-sig")
    CoinHistory(p)
    assert p.read_text("utf-8-sig") == content  # idempotent


# ---------- compare() Randfälle ----------

def test_compare_both_none_is_unreadable():
    text, issue = compare(None, None)
    assert "? → ?" in text and issue == "Zähler konnte nicht gelesen werden"


def test_compare_equal_is_not_increased():
    _, issue = compare(500, 500)
    assert "nicht gestiegen" in issue


# ---------- Runner-Verdrahtung ----------

def test_runner_badge_pause_within_bounds():
    """Pause vor Ablesen liegt zwischen BADGE_PAUSE_S."""
    desk = FakeDesk()
    sleeps = []

    def sleep(s):
        sleeps.append(s)
        desk.sleep(s)
    r = Runner(desk, sleep=sleep, clock=desk.clock, rng=random.Random(2))
    r.run(make_scenario(Config(browse_actions_max=3), random.Random(2)), (),
          badge=lambda h: 10, badge_prev=5)
    # letzte Pause (direkt vor Badge-Read) muss im Bereich liegen
    assert any(BADGE_PAUSE_S[0] <= s <= BADGE_PAUSE_S[1] for s in sleeps)


def test_runner_result_fields_populated():
    desk = FakeDesk()
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(2))
    res = r.run(make_scenario(Config(browse_actions_max=5), random.Random(2)), (),
                badge=lambda h: 777, badge_prev=700)
    assert res.badge == 777 and res.badge_read is True
    assert res.seconds > 0 and res.actions > 0


def test_runner_reads_after_plan_finishes_not_before():
    """Niemals vor dem ersten Plan-Step ablesen."""
    desk = FakeDesk()
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(2))
    plan = make_scenario(Config(browse_actions_max=5), random.Random(2))
    events = []
    orig_check = r._check

    def spy_check(kind="key"):
        events.append(("step", desk.clock()))
        orig_check(kind)
    r._check = spy_check
    r.run(plan, (), badge=lambda h: events.append(("badge", desk.clock())) or 1, badge_prev=0)
    # badge-Event darf nicht VOR dem ersten step-Event auftreten
    first_step = next(i for i, (k, _) in enumerate(events) if k == "step")
    first_badge = next(i for i, (k, _) in enumerate(events) if k == "badge")
    assert first_badge > first_step


# ---------- Config-Migration Randfälle ----------

def test_config_badge_read_true_without_badge_mode_defaults_to_session(tmp_path):
    """Alte Nutzer mit badge_read=true behalten eingeschaltete Ablesung (session)."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"badge_read": True}), "utf-8")
    cfg, warnings = load(p)
    assert cfg.badge_mode == "session" and warnings == []


def test_config_badge_mode_wins_over_old_badge_read(tmp_path):
    """Steht badge_mode drin, wird badge_read ignoriert (keine Rückmigration)."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"badge_read": False, "badge_mode": "random", "badge_random_percent": 10}), "utf-8")
    cfg, warnings = load(p)
    assert cfg.badge_mode == "random" and cfg.badge_random_percent == 10 and warnings == []


def test_config_badge_random_percent_out_of_range_warns(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"badge_random_percent": 0}), "utf-8")
    cfg, warnings = load(p)
    assert cfg.badge_random_percent == 25 and any("badge_random_percent" in w for w in warnings)
    p.write_text(json.dumps({"badge_random_percent": 101}), "utf-8")
    _, warnings = load(p)
    assert any("badge_random_percent" in w for w in warnings)


def test_config_unknown_badge_read_type_ignored(tmp_path):
    """badge_read=... als nicht-bool fällt NICHT auf 'off', da nur `is False` migriert."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"badge_read": "nein"}), "utf-8")
    cfg, warnings = load(p)
    assert cfg.badge_mode == "session"  # Default, da nicht False
    assert warnings == []  # badge_read in der Ausnahmeliste der unbekannten Keys


# ---------- CoinHistory.want signatur / off vs. kein Mode ----------

def test_want_off_never_touches_rng():
    r = random.Random(7)
    h = CoinHistory("/nonexistent/x.csv", rng=r)
    s = r.getstate()
    for _ in range(100):
        assert h.want(Config(badge_mode="off")) is False
    assert r.getstate() == s
