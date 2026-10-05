"""Buttons eines Cookie-/Datenschutz-Hinweises per UI Automation im eigenen Fenster finden (nur Windows).

- Gesucht wird nur im Seiteninhalt (größtes sichtbares Dokument = aktiver Tab), nie in der Browser-Oberfläche.
- Eigenschaften werden in einem Rutsch abgefragt (CacheRequest) – schnell genug, um mehrmals nachzusehen.
- Banner ohne echte Button-Rolle (klickbare div/span) werden über ihren genauen Text gefunden.
"""
import logging

from .badge_win import TOOLBAR_MAX_PX, _automation
from .consent import choose

log = logging.getLogger(__name__)

MAX_NAME = 60
MIN_PX = 8
STRICT_NAMES = ("Alle akzeptieren", "Akzeptieren", "Alle Cookies akzeptieren", "Allen zustimmen", "Zustimmen",
                "Accept all", "Accept", "Accept all cookies", "Ich stimme zu", "Einverstanden", "Alle zulassen",
                "Alle ablehnen", "Ablehnen", "Reject all", "Nur notwendige Cookies", "Nur notwendige",
                "Akzeptieren und weiter", "Zustimmen und weiter", "I agree", "Agree")


def _cache(uia, ids):
    cr = uia.CreateCacheRequest()
    for pid in ids:
        cr.AddProperty(pid)
    return cr


def _elements(found):
    for i in range(found.Length if found else 0):
        yield found.GetElement(i)


def _content(uia, root, cr, ids):
    """Größtes sichtbares Dokument (Seiteninhalt des aktiven Tabs) und seine Oberkante."""
    doc_cond = uia.CreatePropertyCondition(ids.UIA_ControlTypePropertyId, ids.UIA_DocumentControlTypeId)
    best, area = None, 0
    for e in _elements(root.FindAllBuildCache(ids.TreeScope_Descendants, doc_cond, cr)):
        r = e.CachedBoundingRectangle
        a = max(r.right - r.left, 0) * max(r.bottom - r.top, 0)
        if not e.CachedIsOffscreen and a > area:
            best, area = e, a
    if best is None:
        return root, root.CurrentBoundingRectangle.top + TOOLBAR_MAX_PX
    return best, best.CachedBoundingRectangle.top


def _collect(found, top) -> list:
    out = []
    for e in _elements(found):
        name = (e.CachedName or "").strip()
        if not name or len(name) > MAX_NAME or e.CachedIsOffscreen or not e.CachedIsEnabled:
            continue
        r = e.CachedBoundingRectangle
        if r.right - r.left < MIN_PX or r.bottom - r.top < MIN_PX or r.top < top:
            continue
        out.append((name, (r.left, r.top, r.right, r.bottom)))
    return out


def find_consent_button(hwnd: int, decline: bool = False):
    """(Art, Name, (l, t, r, b)) des passenden sichtbaren Buttons im Seiteninhalt oder None."""
    uia = _automation()
    import comtypes.gen.UIAutomationClient as ids
    cr = _cache(uia, (ids.UIA_NamePropertyId, ids.UIA_BoundingRectanglePropertyId, ids.UIA_IsOffscreenPropertyId,
                      ids.UIA_IsEnabledPropertyId))
    root = uia.ElementFromHandle(hwnd)
    base, top = _content(uia, root, cr, ids)
    controls = uia.CreateOrCondition(
        uia.CreatePropertyCondition(ids.UIA_ControlTypePropertyId, ids.UIA_ButtonControlTypeId),
        uia.CreatePropertyCondition(ids.UIA_ControlTypePropertyId, ids.UIA_HyperlinkControlTypeId))
    hit = choose(_collect(base.FindAllBuildCache(ids.TreeScope_Descendants, controls, cr), top), decline)
    if hit:
        return hit
    ignore_case = getattr(ids, "PropertyConditionFlags_IgnoreCase", 1)
    names = None
    for n in STRICT_NAMES:
        c = uia.CreatePropertyConditionEx(ids.UIA_NamePropertyId, n, ignore_case)
        names = c if names is None else uia.CreateOrCondition(names, c)
    return choose(_collect(base.FindAllBuildCache(ids.TreeScope_Descendants, names, cr), top), decline)
