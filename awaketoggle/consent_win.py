"""Zustimmungs-Button eines Cookie-/Datenschutz-Hinweises per UI Automation im eigenen Fenster finden."""
import logging

from .badge_win import TOOLBAR_MAX_PX, _automation
from .consent import best_button

log = logging.getLogger(__name__)


def find_accept_button(hwnd: int):
    """(Name, (l, t, r, b)) des besten sichtbaren Zustimmungs-Buttons im Seiteninhalt oder None."""
    uia = _automation()
    from comtypes.gen.UIAutomationClient import (TreeScope_Descendants, UIA_ButtonControlTypeId,
                                                 UIA_ControlTypePropertyId, UIA_DocumentControlTypeId,
                                                 UIA_HyperlinkControlTypeId)
    root = uia.ElementFromHandle(hwnd)
    # nur im Seiteninhalt suchen (Dokument des aktiven Tabs), nie in der Browser-Oberfläche
    doc = root.FindFirst(TreeScope_Descendants,
                         uia.CreatePropertyCondition(UIA_ControlTypePropertyId, UIA_DocumentControlTypeId))
    base = doc if doc else root
    top = base.CurrentBoundingRectangle.top + (0 if doc else TOOLBAR_MAX_PX)
    cond = uia.CreateOrCondition(uia.CreatePropertyCondition(UIA_ControlTypePropertyId, UIA_ButtonControlTypeId),
                                 uia.CreatePropertyCondition(UIA_ControlTypePropertyId, UIA_HyperlinkControlTypeId))
    found = base.FindAll(TreeScope_Descendants, cond)
    buttons = []
    for i in range(found.Length):
        e = found.GetElement(i)
        name = e.CurrentName or ""
        if not name or len(name) > 60 or e.CurrentIsOffscreen or not e.CurrentIsEnabled:
            continue
        r = e.CurrentBoundingRectangle
        if r.right - r.left < 8 or r.bottom - r.top < 8 or r.top < top:
            continue
        buttons.append((name, (r.left, r.top, r.right, r.bottom)))
    return best_button(buttons)
