"""Zähler (Badge) einer Browser-Erweiterung: Zahl aus Text holen und vorher/nachher vergleichen."""
import re

_NUM = re.compile(r"(\d+(?:[.,]\d+)?)\s*([kKmM])?(?![\w])")


def parse_number(text):
    """Erste Zahl im Text, z. B. '698', '1.2k', 'Punkte: 1,5M'; None wenn keine."""
    m = _NUM.search(text or "")
    if not m:
        return None
    raw, suffix = m.group(1), (m.group(2) or "").lower()
    if suffix:
        return float(raw.replace(",", ".")) * (1000 if suffix == "k" else 1_000_000)
    return int(raw.replace(".", "").replace(",", ""))


_PLAIN = re.compile(r"^[^\w]*(\d{1,3}(?:[., \u00a0\u202f]\d{3})+|\d+)\s*$")
POPUP_TITLE = "power coins"


def parse_popup(texts, title=POPUP_TITLE):
    """Große Zahl im Popup (z. B. 'Power Coins' … '1,341'): erste Zeile nach dem Titel, die nur aus einer
    Zahl besteht. Ohne Titel None – sonst würde die Zahl eines fremden Popups (z. B. Schutzschild „0“) gezählt."""
    lines = [ln.strip() for t in texts for ln in (t or "").splitlines() if ln.strip()]
    start = next((i for i, ln in enumerate(lines) if title in ln.lower()), None)
    if start is None:
        return None
    for ln in lines[start:]:
        m = _PLAIN.match(ln)
        if m:
            return int(re.sub(r"\D", "", m.group(1)))
    return None


def compare(before, after):
    """Liefert (Text für Tooltip/Protokoll, Auffälligkeit oder None); before = letzter bekannter Wert."""
    if after is None:
        return f"Zähler {before if before is not None else '?'} → ?", "Zähler konnte nicht gelesen werden"
    if before is None:
        return f"Zähler {after}", None
    text = f"Zähler {before} → {after}"
    if after <= before:
        return text, f"Zähler nicht gestiegen ({before} → {after})"
    return text, None
