"""v1.10 adversarial: Edge-Cases rund um den Power-Coins-Zähler."""
import pytest

from awaketoggle import badge_win
from awaketoggle.badge import parse_popup
from tests.test_v18 import BROWSER, BUTTON, POPUP, Desk


def _read(desk):
    return badge_win.read_popup(BROWSER, BUTTON, desk, sleep=desk.sleep, clock=desk.clock)


# --- _settled ---------------------------------------------------------------

def test_popup_never_settles_returns_last_seen(monkeypatch):
    """Zahl ändert sich bis zum Timeout: letzter beobachteter Wert, keine Hänge-Schleife."""
    seq = iter(range(1, 10_000))

    def texts(h):
        return ["Power Coins", str(next(seq))]
    monkeypatch.setattr(badge_win, "popup_texts", texts)
    monkeypatch.setattr(badge_win, "_ocr", lambda r: "")
    v = _read(Desk())
    assert isinstance(v, int) and v > 0


def test_settled_returns_none_if_never_a_number(monkeypatch):
    monkeypatch.setattr(badge_win, "popup_texts", lambda h: ["irgendwas ohne Titel"])
    monkeypatch.setattr(badge_win, "_ocr", lambda r: "")
    assert _read(Desk()) is None


# --- Exceptions -------------------------------------------------------------

def test_popup_texts_exception_falls_back_to_ocr(monkeypatch):
    def boom(h):
        raise RuntimeError("UIA kaputt")
    monkeypatch.setattr(badge_win, "popup_texts", boom)
    monkeypatch.setattr(badge_win, "_ocr", lambda r: "Power Coins\n1,341")
    assert _read(Desk()) == 1341


def test_ocr_exception_is_swallowed_and_returns_none(monkeypatch):
    monkeypatch.setattr(badge_win, "popup_texts", lambda h: [])
    def boom(r):
        raise OSError("powershell weg")
    monkeypatch.setattr(badge_win, "_ocr", boom)
    assert _read(Desk()) is None


# --- _better / UIA 0 + OCR > 0 ---------------------------------------------

def test_uia_zero_overridden_by_positive_ocr(monkeypatch):
    monkeypatch.setattr(badge_win, "popup_texts", lambda h: ["Power Coins", "0"])
    monkeypatch.setattr(badge_win, "_ocr", lambda r: "Power Coins\n1,341")
    assert _read(Desk()) == 1341


def test_better_prefers_known_zero_over_none():
    assert badge_win._better(None, 0) == 0
    assert badge_win._better(0, None) == 0
    assert badge_win._better(0, 5) == 5
    assert badge_win._better(5, 0) == 5
    assert badge_win._better(None, None) is None


# --- _rank / NOT_COUNTER ----------------------------------------------------

def test_guard_class_rejected_even_with_power_coins_name():
    guard = ("Power Coins", "Power Coins", "PowerGuardButtonView", (0, 0, 1, 1), None)
    assert badge_win._rank(guard) is None


def test_extensions_toolbar_rejected():
    b = ("Erweiterungen", "", "ExtensionsToolbarButton", (0, 0, 1, 1), None)
    assert badge_win._rank(b) is None


def test_class_coin_ranks_before_name_tooltip():
    cls_coin = ("x", "", "CoinActionView", (0, 0, 1, 1), None)
    name_only = ("y", "Power Coins", "ToolbarButton", (0, 0, 1, 1), None)
    got = badge_win._candidates([name_only, cls_coin])
    assert got[0] is cls_coin and got[1] is name_only


# --- parse_popup edge cases -------------------------------------------------

def test_parse_popup_requires_title_strictly():
    assert parse_popup(["Shield", "1,341"]) is None
    assert parse_popup(["POWER COINS", "1,341"]) == 1341  # case-insensitive
    assert parse_popup(["intro Power Coins intro", "1,341"]) == 1341


def test_parse_popup_ignores_mixed_lines_until_plain_number():
    # Zahl mit Zusatztext wird übersprungen, bis eine reine Zahl kommt
    assert parse_popup(["Power Coins", "Platz 12 von 99", "3 hrs 4 min", "1,341"]) == 1341


def test_parse_popup_handles_narrow_nbsp_thousands():
    assert parse_popup(["Power Coins", "1\u202f341"]) == 1341
    assert parse_popup(["Power Coins", "1\u00a0341"]) == 1341


# --- _popup_windows filtering ----------------------------------------------

def test_popup_windows_ignores_hidden_wrong_proc_small():
    desk = Desk()
    # Vor dem Klick: Fenster schon vorhanden aber unsichtbar => zählt als "before"? nein,
    # before merkt sich nur sichtbare. Hidden existierendes Popup muss nach Klick erkannt werden.
    desk.wins[POPUP] = (0, 50, 540, 350)
    # bleibt hidden; _popup_windows soll es nicht liefern
    before = {h for h in desk.top_windows() if desk.is_visible(h)}
    assert badge_win._popup_windows(desk, BROWSER, "power.exe", before) == []
    # jetzt sichtbar
    desk.visible.add(POPUP)
    assert badge_win._popup_windows(desk, BROWSER, "power.exe", before) == [POPUP]
    # falscher Prozess
    assert badge_win._popup_windows(desk, BROWSER, "andere.exe", before) == []


def test_popup_windows_too_small_rejected():
    desk = Desk()
    desk.wins[POPUP] = (0, 50, 10, 60)  # 10x10 < POPUP_MIN_PX
    desk.visible.add(POPUP)
    before = set()
    assert badge_win._popup_windows(desk, BROWSER, "power.exe", before) == []


# --- Close popup fallback ---------------------------------------------------

def test_popup_closes_via_second_click_when_esc_fails(monkeypatch):
    monkeypatch.setattr(badge_win, "popup_texts", lambda h: ["Power Coins", "1,341"])
    desk = Desk(esc_closes=False)
    assert _read(desk) == 1341
    clicks = [e for e in desk.log if e[0] == "click"]
    assert len(clicks) == 2  # einmal zum Öffnen, einmal zum Schließen
    assert POPUP not in desk.wins


# --- read_badge: no buttons at all -----------------------------------------

def test_read_badge_without_any_counter_button_returns_none(monkeypatch):
    monkeypatch.setattr(badge_win, "toolbar_buttons",
                        lambda h: [("Zurück", "", "BackButton", (0, 0, 1, 1), None)])
    assert badge_win.read_badge(BROWSER, popup=True, desk=object()) is None


def test_read_badge_toolbar_exception_returns_none(monkeypatch):
    def boom(h):
        raise RuntimeError("UIA weg")
    monkeypatch.setattr(badge_win, "toolbar_buttons", boom)
    assert badge_win.read_badge(BROWSER, popup=True, desk=object()) is None
