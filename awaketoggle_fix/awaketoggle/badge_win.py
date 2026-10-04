"""Zähler einer Erweiterung von außen lesen: UI Automation (Name/Tooltip), sonst Windows-OCR auf den Button."""
import logging
import os
import subprocess
import tempfile

from .badge import parse_number

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
    from comtypes.gen.UIAutomationClient import (TreeScope_Descendants, UIA_ButtonControlTypeId,
                                                 UIA_ControlTypePropertyId, UIA_MenuItemControlTypeId)
    uia = _automation()
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
                    (r.left, r.top, r.right, r.bottom)))
    return out


def _ocr(rect) -> str:
    from PIL import ImageGrab, ImageOps
    img = ImageGrab.grab(bbox=rect, all_screens=True).convert("L")
    img = ImageOps.autocontrast(img.resize((img.width * OCR_SCALE, img.height * OCR_SCALE)))
    path = os.path.join(tempfile.gettempdir(), "AwakeToggle-badge.png")
    img.save(path)
    out = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", OCR_PS, path],
                         capture_output=True, text=True, timeout=30,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if out.returncode:
        log.debug("OCR fehlgeschlagen: %s", out.stderr.strip()[:300])
    return out.stdout.strip()


def _is_extension(name, help_text, cls) -> bool:
    return "toolbaraction" in cls.lower() or "extension" in cls.lower()


def read_badge(hwnd: int, extension: str = ""):
    """Zahl des Zählers oder None. extension = Teil des Erweiterungsnamens (leer = automatisch)."""
    try:
        buttons = toolbar_buttons(hwnd)
    except Exception:
        log.exception("UI Automation nicht verfügbar")
        return None
    want = extension.lower()
    if want:
        buttons = [b for b in buttons if want in b[0].lower() or want in b[1].lower()]
    else:
        ext = [b for b in buttons if _is_extension(*b[:3])]
        buttons = ext or buttons
    for name, help_text, _, _ in buttons:
        for text in (name, help_text):
            n = parse_number(text)
            if n is not None:
                return n
    targets = buttons if want else [b for b in buttons if _is_extension(*b[:3])]
    for b in targets:
        try:
            n = parse_number(_ocr(b[3]))
        except Exception:
            log.exception("OCR auf Erweiterungs-Button fehlgeschlagen")
            return None
        if n is not None:
            return n
    return None
