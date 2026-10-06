"""Tabs eines Browserfensters per UI Automation lesen (nur Windows).

Gelesen wird nur die Browser-Oberfläche (Tableiste, auch vertikale Tabs); Seiteninhalte (Dokumente) werden
übersprungen, damit Reiter auf Webseiten nie als Browser-Tabs gelten.
"""
from .badge_win import _automation
from .consent_win import _cache

MAX_NODES = 2000


def list_tabs(hwnd: int) -> list:
    """[(Tab-ID, ausgewählt)] in Reihenfolge der Tableiste; Tab-ID = UIA-RuntimeId (gilt, solange der Tab lebt)."""
    uia = _automation()
    import comtypes.gen.UIAutomationClient as ids
    cr = _cache(uia, (ids.UIA_ControlTypePropertyId, ids.UIA_SelectionItemIsSelectedPropertyId))
    walker = uia.ControlViewWalker
    out, budget = [], [MAX_NODES]

    def walk(e):
        child = walker.GetFirstChildElementBuildCache(e, cr)
        while child and budget[0] > 0:
            budget[0] -= 1
            kind = child.CachedControlType
            if kind == ids.UIA_TabItemControlTypeId:
                selected = child.GetCachedPropertyValue(ids.UIA_SelectionItemIsSelectedPropertyId)
                out.append((tuple(child.GetRuntimeId()), bool(selected)))
            elif kind != ids.UIA_DocumentControlTypeId:
                walk(child)
            child = walker.GetNextSiblingElementBuildCache(child, cr)

    walk(uia.ElementFromHandleBuildCache(hwnd, cr))
    return out
