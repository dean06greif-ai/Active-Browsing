"""v1.10.0: Power-Coins-Zähler liest die echte Zahl (1,341) statt 0."""
from awaketoggle import badge_win
from awaketoggle.badge import parse_popup
from tests.test_v18 import BROWSER, BUTTON, POPUP, Desk

GUARD = ("Power Coins", "", "PowerGuardButtonView", (150, 10, 190, 40), None)
SHIELD = ("Schutz", "0 blockiert", "ToolbarBadgeView", (150, 10, 190, 40), None)


def _read(desk):
    return badge_win.read_popup(BROWSER, BUTTON, desk, sleep=desk.sleep, clock=desk.clock)


def _count_up(values):
    calls = []

    def texts(h):
        calls.append(h)
        return ["Power Coins", "Rise to the Top with Power Coins", values[min(len(calls), len(values)) - 1],
                "Today's Activity", "3 hrs 4 min", "Cumulative Usage", "22 hrs 21 min"]
    return texts


def test_popup_counting_up_from_zero_reads_final_value(monkeypatch):
    monkeypatch.setattr(badge_win, "popup_texts", _count_up(["0", "0", "0", "0", "0", "312", "880", "1,290", "1,341"]))
    monkeypatch.setattr(badge_win, "_ocr", lambda r: "")
    assert _read(Desk()) == 1341


def test_value_still_changing_is_not_taken_early(monkeypatch):
    monkeypatch.setattr(badge_win, "popup_texts", _count_up(["1,340", "1,341"]))
    assert _read(Desk()) == 1341


def test_only_zero_in_uia_uses_ocr_value(monkeypatch):
    monkeypatch.setattr(badge_win, "popup_texts", _count_up(["0"]))
    monkeypatch.setattr(badge_win, "_ocr", lambda r: "Power Coins\nRise to the Top with Power Coins\n1,341\n3 hrs 4 min")
    assert _read(Desk()) == 1341


def test_really_zero_stays_zero(monkeypatch):
    monkeypatch.setattr(badge_win, "popup_texts", _count_up(["0"]))
    monkeypatch.setattr(badge_win, "_ocr", lambda r: "Power Coins\n0")
    assert _read(Desk()) == 0


def test_hidden_reused_popup_window_is_found(monkeypatch):
    desk = Desk()
    desk.wins[POPUP] = (0, 50, 540, 350)
    orig = desk.click

    def click():
        desk.log.append(("click", desk.pos))
        desk.visible.add(POPUP) if POPUP not in desk.visible else orig()
    desk.click = click
    monkeypatch.setattr(badge_win, "popup_texts", _count_up(["1,341"]))
    assert _read(desk) == 1341


def test_popup_inside_browser_window_is_read_by_ocr_below_badge(monkeypatch):
    rects = []
    monkeypatch.setattr(badge_win, "popup_texts", lambda h: [])
    monkeypatch.setattr(badge_win, "_ocr", lambda r: rects.append(r) or "Power Coins\nRise to the Top\n1,341")
    desk = Desk(popup_appears=False)
    assert _read(desk) == 1341
    assert rects[0] == (0, 40, 570, 690)
    assert ("key", (badge_win.VK_ESCAPE,)) in desk.log and desk.pos == (500, 500)


def test_foreign_popup_without_title_is_not_counted():
    assert parse_popup(["0 Werbung blockiert", "0"]) is None
    assert parse_popup(["Schutz", "0"]) is None
    assert parse_popup(["Power Coins", "1,341"]) == 1341


def test_coins_button_preferred_over_badge_class_and_guard():
    got = badge_win._candidates([SHIELD, GUARD, ("x", "Power Coins", "ToolbarButton", (0, 0, 1, 1), None)])
    assert [b[2] for b in got] == ["ToolbarButton", "ToolbarBadgeView"]
    got = badge_win._candidates([SHIELD, BUTTON])
    assert got[0] == BUTTON


def test_read_badge_tries_next_button_when_first_popup_has_no_coins(monkeypatch):
    other = ("Power Coins", "", "ToolbarActionView", (200, 10, 240, 40), None)
    monkeypatch.setattr(badge_win, "toolbar_buttons", lambda h: [other, BUTTON])
    seen = []
    monkeypatch.setattr(badge_win, "read_popup", lambda h, b, d: seen.append(b) or (1341 if b is BUTTON else None))
    assert badge_win.read_badge(BROWSER, popup=True, desk=object()) == 1341
    assert seen == [BUTTON]
    third = ("Power Coins Shop", "", "X", (0, 0, 1, 1), None)
    monkeypatch.setattr(badge_win, "toolbar_buttons", lambda h: [third, other])
    seen.clear()
    assert badge_win.read_badge(BROWSER, popup=True, desk=object()) is None
    assert seen == [third, other]
