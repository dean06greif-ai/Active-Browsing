"""Adversarial tests for v1.8 (Power Coins popup + history)."""
from datetime import datetime

import pytest

from awaketoggle import badge_win
from awaketoggle.badge import parse_popup
from awaketoggle.history import CoinHistory
from awaketoggle.tray_labels import tooltip
from awaketoggle.core import Status
from tests.test_v18 import BROWSER, POPUP, TIP, BUTTON, Desk, _read


# --- parse_popup edge cases ---

def test_parse_popup_ignores_badge_short_notation_and_leading_junk():
    # "1k" short-form must NOT be considered the big number
    assert parse_popup(["Power Coins", "1k"]) is None
    # thousands with non-breaking / narrow space separators
    assert parse_popup(["Power Coins", "12\u00a0345"]) == 12345
    assert parse_popup(["Power Coins", "12\u202f345"]) == 12345
    # suffix text on the number line should not match (plain number only)
    assert parse_popup(["Power Coins", "487 Coins"]) is None
    # negative sign ignored (just number)
    assert parse_popup(["Power Coins", "-487"]) == 487


def test_parse_popup_handles_all_none_or_empty():
    assert parse_popup([]) is None
    assert parse_popup([None, None]) is None
    assert parse_popup(["", "   "]) is None


# --- read_popup: popup never gets text ---

def test_read_popup_returns_none_when_popup_never_has_number(monkeypatch):
    # UIA keeps returning title only; OCR also yields no number
    monkeypatch.setattr(badge_win, "popup_texts", lambda h: ["Power Coins"])
    monkeypatch.setattr(badge_win, "_ocr", lambda rect: "Power Coins\nloading...")
    desk = Desk()
    assert _read(desk) is None
    # popup still gets closed and cursor restored
    assert POPUP not in desk.wins
    assert desk.pos == (500, 500)


# --- read_popup: tooltip-sized windows are not picked as popup ---

def test_read_popup_ignores_small_tooltip_windows(monkeypatch):
    # TIP window (80x20) is below POPUP_MIN_PX, must be skipped; big POPUP wins
    def texts(h):
        return ["Power Coins", "487"] if h == POPUP else pytest.fail(f"wrong hwnd {h}")
    monkeypatch.setattr(badge_win, "popup_texts", texts)
    desk = Desk()
    assert _read(desk) == 487


# --- read_popup: largest popup wins when multiple appear ---

def test_read_popup_picks_largest_candidate_popup(monkeypatch):
    desk = Desk()
    # Patch click so two popups appear - a small valid one and the big one
    orig_click = desk.click

    def click():
        orig_click()
        # Add a smaller same-process window (still above min)
        desk.wins[99] = (0, 0, 130, 90)
        desk.visible.add(99)
    desk.click = click
    monkeypatch.setattr(badge_win, "popup_texts",
                        lambda h: ["Power Coins", "487"] if h == POPUP else ["Power Coins", "1"])
    assert _read(desk) == 487


# --- history: garbage rows in CSV ---

def test_history_csv_with_garbage_rows_is_tolerated(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text(
        "Zeit;Wert;Änderung\n"
        ";;\n"
        "oops\n"
        "2026-06-10 12:00:00;480;0\n"
        "2026-06-10 12:01:00;not-a-number;5\n"
        "2026-06-10 12:02:00;487;7\n"
        "short;row\n",
        "utf-8-sig",
    )
    h = CoinHistory(p)
    assert h.rows() == [("2026-06-10 12:00:00", 480, 0), ("2026-06-10 12:02:00", 487, 7)]
    assert h.last == 487
    assert h.label() == "Power Coins: 487"


def test_history_record_accepts_float_and_logs_unreadable(tmp_path):
    times = iter(datetime(2026, 1, 1, 10, m) for m in range(5))
    h = CoinHistory(tmp_path / "c.csv", now=lambda: next(times))
    assert h.record(None) is None
    assert h.record(100.9) == 100  # truncates like int()
    assert h.record(105) == 105
    assert h.rows()[-1] == ("2026-01-01 10:02:00", 105, 5)
    assert h.records()[0][8] == "nicht lesbar" and h.records()[0][1] == ""


def test_history_label_before_any_read(tmp_path):
    h = CoinHistory(tmp_path / "c.csv")
    assert h.label() == "Power Coins: noch nicht gelesen"


# --- tooltip length guard ---

def test_tooltip_never_exceeds_127_even_with_long_coins_line():
    s = Status("on", "x" * 300, datetime(2026, 6, 10, 18, 0))
    t = tooltip(s, "Power Coins: 999999 (+123456 seit Programmstart)")
    assert len(t) <= 127
    assert "Power Coins: 999999" in t
