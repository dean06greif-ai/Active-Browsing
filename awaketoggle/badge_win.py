"""Zähler einer Erweiterung von außen lesen.

Standard: Badge anklicken, im Popup („Power Coins“) die große Zahl lesen (UI Automation, sonst OCR), Popup schließen.
Alternativ (popup=False): Zahl auf dem Button selbst (Name/Tooltip, sonst OCR), z. B. „1k“.
"""
import logging
import os
import subprocess
import tempfile
import time

from .badge import parse_number, parse_popup

log = logging.getLogger(__name__)

TOOLBAR_MAX_PX = 160
OCR_SCALE = 5
OCR_PS = r"""
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics,ContentType=WindowsRuntime]
$m=([System.WindowsRuntimeSystemExtensions].GetMethods()|?{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'})[0]
function A($o,$t){$k=$m.MakeGenericMethod($t).Invoke($null,@($o));$k.Wait(-1)|Out-Null;$k.Result}
$f=A ([Windows.Storage.StorageFile]::GetFileFromPathAsync($args[0])) ([Windows.Storage.StorageFile])
$s=A ($f.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$d=A ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($s)) ([Windows.Graphics.Imaging.BitmapDecoder])
$b=A ($d.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$e=[Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
(A ($e.RecognizeAsync($b)) ([Windows.Media.Ocr.OcrResult])).Text
"""

_uia = None


def _automation():
    global _uia
    import comtypes
    import comtypes.client
    try:
        comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
    except OSError:
        pass
    if _uia is None:
        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation
        _uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
    return _uia


def toolbar_buttons(hwnd: int) -> list:
    """Buttons oben im Browserfenster: [(Name, Hilfetext, Klasse, (l, t, r, b))]."""
    uia = _automation()
    from comtypes.gen.UIAutomationClient import (TreeScope_Descendants, UIA_ButtonControlTypeId,
                                                 UIA_ControlTypePropertyId, UIA_MenuItemControlTypeId)
    root = uia.ElementFromHandle(hwnd)
    top = root.CurrentBoundingRectangle.top
    cond = uia.CreateOrCondition(uia.CreatePropertyCondition(UIA_ControlTypePropertyId, UIA_ButtonControlTypeId),
                                 uia.CreatePropertyCondition(UIA_ControlTypePropertyId, UIA_MenuItemControlTypeId))
    found = root.FindAll(TreeScope_Descendants, cond)
    out = []
    for i in range(found.Length):
        e = found.GetElement(i)
        r = e.CurrentBoundingRectangle
        if r.right - r.left <= 0 or r.top - top > TOOLBAR_MAX_PX:
            continue
        out.append((e.CurrentName or "", e.CurrentHelpText or "", e.CurrentClassName or "",
                    (r.left, r.top, r.right, r.bottom), e))
    return out


def _ocr(rect) -> str:
    from PIL import ImageGrab, ImageOps
    img = ImageGrab.grab(bbox=rect, all_screens=True).convert("L")
    img = ImageOps.autocontrast(img.resize((img.width * OCR_SCALE, img.height * OCR_SCALE)))
    if sum(img.getdata()) / (img.width * img.height) < 128:
        img = ImageOps.invert(img)
    path = os.path.join(tempfile.gettempdir(), "AwakeToggle-badge.png")
    img.save(path)
    out = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", OCR_PS, path],
                         capture_output=True, text=True, timeout=30,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if out.returncode:
        log.debug("OCR fehlgeschlagen: %s", out.stderr.strip()[:300])
    return out.stdout.strip()


COUNTER_HINTS = ("points", "coin", "badge", "counter", "actionview")


def _rank(button) -> int:
    """0 = sicher ein Zähler-Button, höher = unwahrscheinlicher, None = kein Kandidat."""
    name, cls = button[0].lower(), button[2].lower()
    for i, hint in enumerate(COUNTER_HINTS):
        if hint in cls:
            return i
    if "coin" in name or "point" in name:
        return len(COUNTER_HINTS)
    return None


def _candidates(buttons) -> list:
    ranked = [(r, i, b) for i, b in enumerate(buttons) if (r := _rank(b)) is not None]
    return [b for _, _, b in sorted(ranked)]


def _child_texts(element) -> list:
    uia = _automation()
    kids = element.FindAll(TREE_SCOPE_DESCENDANTS, uia.CreateTrueCondition())
    return [kids.GetElement(i).CurrentName or "" for i in range(kids.Length)]


TREE_SCOPE_DESCENDANTS = 4


POPUP_OPEN_S = 4.0
POPUP_TEXT_S = 5.0
POPUP_CLOSE_S = 1.5
POPUP_MIN_PX = (120, 80)
POPUP_POLL_S = 0.15
VK_ESCAPE = 0x1B


def _wait(fn, seconds, sleep, clock):
    end = clock() + seconds
    while True:
        v = fn()
        if (v is not None and v != []) or clock() >= end:
            return v
        sleep(POPUP_POLL_S)


def _popup_windows(desk, hwnd, proc, before) -> list:
    """Neue sichtbare Fenster des Browsers (größtes zuerst) – das Popup der Erweiterung."""
    found = []
    for h in desk.top_windows() - before:
        if h == hwnd or not desk.is_visible(h) or desk.process_name(h) != proc:
            continue
        left, top, right, bottom = desk.window_rect(h)
        if right - left >= POPUP_MIN_PX[0] and bottom - top >= POPUP_MIN_PX[1]:
            found.append(((right - left) * (bottom - top), h))
    return [h for _, h in sorted(found, reverse=True)]


def popup_texts(hwnd: int) -> list:
    root = _automation().ElementFromHandle(hwnd)
    return [root.CurrentName or ""] + _child_texts(root)


def _popup_value(h):
    try:
        return parse_popup(popup_texts(h))
    except Exception:
        log.debug("Popup-Text nicht lesbar", exc_info=True)
        return None


def read_popup(hwnd, button, desk, sleep=time.sleep, clock=time.monotonic):
    """Badge anklicken, Zahl im Popup lesen, Popup wieder schließen, Maus zurück. None wenn nicht lesbar."""
    proc = desk.process_name(hwnd)
    left, top, right, bottom = button[3]
    cursor = desk.cursor()
    before = desk.top_windows()
    desk.move_to((left + right) // 2, (top + bottom) // 2)
    sleep(0.15)
    desk.click()
    popup = 0
    try:
        popups = _wait(lambda: _popup_windows(desk, hwnd, proc, before), POPUP_OPEN_S, sleep, clock)
        if not popups:
            log.warning("Zähler: nach Klick auf %r ist kein Popup erschienen", button[0])
            return None
        popup = popups[0]
        value = _wait(lambda: _popup_value(popup), POPUP_TEXT_S, sleep, clock)
        if value is None:
            try:
                text = _ocr(desk.window_rect(popup))
                log.debug("OCR Popup: %r", text)
                value = parse_popup(text.splitlines())
            except Exception:
                log.exception("OCR auf Zähler-Popup fehlgeschlagen")
        if value is None:
            log.warning("Zähler: Popup gefunden, aber keine Zahl darin (%r)", desk.title(popup))
        return value
    finally:
        if popup:
            _close_popup(desk, popup, sleep, clock)
        desk.move_to(*cursor)


def _close_popup(desk, popup, sleep, clock):
    gone = lambda: True if not desk.is_window(popup) or not desk.is_visible(popup) else None  # noqa: E731
    desk.send_combo((VK_ESCAPE,))
    if _wait(gone, POPUP_CLOSE_S, sleep, clock):
        return
    log.info("Zähler-Popup reagiert nicht auf Esc, klicke Badge erneut")
    desk.click()
    if not _wait(gone, POPUP_CLOSE_S, sleep, clock):
        log.warning("Zähler-Popup ließ sich nicht schließen")


def _pick(buttons, extension: str) -> list:
    want = extension.lower()
    if want:
        buttons = [b for b in buttons if want in b[0].lower() or want in b[1].lower()]
        return _candidates(buttons) + [b for b in buttons if _rank(b) is None]
    return _candidates(buttons)


def read_badge(hwnd: int, extension: str = "", popup: bool = True, desk=None):
    """Zahl des Zählers oder None. extension = Teil des Erweiterungsnamens (leer = automatisch).

    popup=True: Badge anklicken und die große Zahl im Popup lesen (genauer Wert, z. B. 487 statt „1k“)."""
    try:
        buttons = _pick(toolbar_buttons(hwnd), extension)
    except Exception:
        log.exception("UI Automation nicht verfügbar")
        return None
    if popup:
        if not buttons:
            log.warning("Zähler: kein Erweiterungs-Button gefunden (badge_extension prüfen, --selftest)")
            return None
        if desk is None:
            from .win32 import Desktop
            desk = Desktop()
        return read_popup(hwnd, buttons[0], desk)
    for name, help_text, _, _, element in buttons:
        texts = [name, help_text]
        try:
            texts += _child_texts(element)
        except Exception:
            log.debug("Unterelemente nicht lesbar", exc_info=True)
        for text in texts:
            n = parse_number(text)
            if n is not None:
                return n
    for b in buttons:
        try:
            text = _ocr(b[3])
        except Exception:
            log.exception("OCR auf Zähler-Button fehlgeschlagen")
            return None
        log.debug("OCR %r: %r", b[0], text)
        n = parse_number(text)
        if n is not None:
            return n
    return None
