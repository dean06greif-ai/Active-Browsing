"""v1.8.0: Power-Coins-Zahl aus dem Popup lesen, Verlauf (CSV + HTML), Anzeige im Tooltip."""
from datetime import datetime

import pytest

from awaketoggle import badge_win
from awaketoggle.badge import parse_popup
from awaketoggle.core import Status
from awaketoggle.history import CoinHistory, render_html
from awaketoggle.tray_labels import tooltip

BROWSER, POPUP, TIP = 10, 20, 30
BUTTON = ("Power Coins", "", "PowerPointsActionView", (100, 10, 140, 40), None)


def test_parse_popup_reads_big_number_after_title():
    assert parse_popup(["Power Coins", "Rise to the Top with Power Coins", "487"]) == 487
    assert parse_popup(["Power Coins\nRise to the Top with Power Coins\n487\n"]) == 487
    assert parse_popup(["Level 3", "Power Coins", "Platz 12 von 99", "1.234"]) == 1234
    assert parse_popup(["Power Coins", "@ 487"]) == 487
    assert parse_popup(["Power Coins", "12 345"]) == 12345
    assert parse_popup(["", None, "Power Coins"]) is None
    assert parse_popup(["999", "Power Coins", "487"]) == 487
    assert parse_popup(["487"]) == 487
    assert parse_popup(["1k"]) is None


class Desk:
    def __init__(self, popup_appears=True, esc_closes=True):
        self.wins = {BROWSER: (0, 0, 1200, 800)}
        self.visible = {BROWSER}
        self.popup_appears, self.esc_closes = popup_appears, esc_closes
        self.log, self.pos, self.t = [], (500, 500), 0.0

    def process_name(self, h):
        return "power.exe"

    def cursor(self):
        return self.pos

    def top_windows(self):
        return set(self.wins)

    def move_to(self, x, y):
        self.pos = (x, y)
        self.log.append(("move", x, y))

    def click(self):
        self.log.append(("click", self.pos))
        if POPUP in self.wins:
            self._close()
        elif self.popup_appears:
            self.wins[TIP] = (120, 45, 200, 65)
            self.wins[POPUP] = (0, 50, 540, 350)
            self.visible |= {POPUP, TIP}

    def _close(self):
        self.wins.pop(POPUP, None)
        self.visible.discard(POPUP)

    def send_combo(self, vks):
        self.log.append(("key", vks))
        if self.esc_closes:
            self._close()

    def is_window(self, h):
        return h in self.wins

    def is_visible(self, h):
        return h in self.visible

    def window_rect(self, h):
        return self.wins[h]

    def title(self, h):
        return "Power Coins"

    def sleep(self, s):
        self.t += s

    def clock(self):
        return self.t


def _read(desk):
    return badge_win.read_popup(BROWSER, BUTTON, desk, sleep=desk.sleep, clock=desk.clock)


def test_read_popup_clicks_badge_reads_number_closes_and_restores_mouse(monkeypatch):
    monkeypatch.setattr(badge_win, "popup_texts", lambda h: ["Power Coins", "Rise to the Top", "487"]
                        if h == POPUP else ["Tooltip 1k"])
    desk = Desk()
    assert _read(desk) == 487
    assert ("click", (120, 25)) in desk.log
    assert ("key", (badge_win.VK_ESCAPE,)) in desk.log
    assert POPUP not in desk.wins and desk.pos == (500, 500)


def test_read_popup_waits_until_web_content_is_accessible(monkeypatch):
    calls = []

    def texts(h):
        calls.append(h)
        return ["Power Coins"] if len(calls) < 4 else ["Power Coins", "487"]
    monkeypatch.setattr(badge_win, "popup_texts", texts)
    assert _read(Desk()) == 487 and len(calls) == 4


def test_read_popup_without_popup_returns_none_and_does_not_click_twice(monkeypatch):
    monkeypatch.setattr(badge_win, "popup_texts", lambda h: pytest.fail("kein Popup"))
    desk = Desk(popup_appears=False)
    assert _read(desk) is None
    assert [e for e in desk.log if e[0] == "click"] == [("click", (120, 25))]
    assert desk.pos == (500, 500)


def test_read_popup_falls_back_to_ocr_and_clicks_again_if_esc_fails(monkeypatch):
    monkeypatch.setattr(badge_win, "popup_texts", lambda h: ["Power Coins"])
    monkeypatch.setattr(badge_win, "_ocr", lambda rect: "Power Coins\nRise to the Top with Power Coins\n487")
    desk = Desk(esc_closes=False)
    assert _read(desk) == 487
    assert len([e for e in desk.log if e[0] == "click"]) == 2 and POPUP not in desk.wins


def test_read_badge_popup_uses_first_counter_button(monkeypatch):
    buttons = [("Neu laden", "", "ReloadButton", (0, 0, 1, 1), None), BUTTON]
    monkeypatch.setattr(badge_win, "toolbar_buttons", lambda h: buttons)
    seen = []
    monkeypatch.setattr(badge_win, "read_popup", lambda h, b, d: seen.append(b) or 487)
    assert badge_win.read_badge(BROWSER, popup=True, desk=object()) == 487
    assert seen == [BUTTON]
    monkeypatch.setattr(badge_win, "toolbar_buttons", lambda h: buttons[:1])
    assert badge_win.read_badge(BROWSER, popup=True, desk=object()) is None


def test_history_records_csv_label_and_html(tmp_path):
    times = iter(datetime(2026, 6, 10, 12, m) for m in range(10))
    h = CoinHistory(tmp_path / "power_coins.csv", now=lambda: next(times))
    changes = []
    h.on_change = lambda: changes.append(h.last)
    assert h.label() == "Power Coins: noch nicht gelesen"
    assert h.record(None) is None and changes == []
    h.record(480)
    h.record(487)
    h.record(1000.0)
    assert h.rows() == [("2026-06-10 12:01:00", 480, 0), ("2026-06-10 12:02:00", 487, 7),
                        ("2026-06-10 12:03:00", 1000, 513)]
    assert h.label() == "Power Coins: 1000 (+520 seit Programmstart)"
    assert changes == [480, 487, 1000]
    text = (tmp_path / "power_coins.csv").read_text("utf-8-sig")
    assert text.splitlines()[0].startswith("Zeit;Wert;Änderung;Minuten seit letzter Messung;")
    assert text.splitlines()[1].startswith("2026-06-10 12:00:00;;;") and "nicht lesbar" in text
    page = (tmp_path / "power_coins.html").read_text("utf-8")
    assert 'id="coins-current">1000<' in page and "<polyline" in page and "+513" in page
    again = CoinHistory(tmp_path / "power_coins.csv")
    assert again.last == 1000 and again.label() == "Power Coins: 1000"


def test_history_skips_broken_rows_and_renders_empty(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("Zeit;Wert;Änderung\nkaputt\n2026-06-10 12:00:00;487;0\n", "utf-8-sig")
    assert CoinHistory(p).rows() == [("2026-06-10 12:00:00", 487, 0)]
    assert "ab zwei Messwerten" in render_html([], p)


def test_tooltip_keeps_coins_line_visible():
    s = Status("on", "An, Browser-Test 12:00: Zähler 480 → 487, " + "x" * 200, datetime(2026, 6, 10, 18, 0))
    t = tooltip(s, "Power Coins: 487 (+7 seit Programmstart)")
    assert len(t) <= 127 and t.endswith("\nAuto-Aus um 18:00\nPower Coins: 487 (+7 seit Programmstart)")
    assert tooltip(Status("off", "Aus")) == "AwakeToggle: Aus"
