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


def compare(before, after):
    """Liefert (Text für Tooltip/Protokoll, Auffälligkeit oder None)."""
    if before is None and after is None:
        return "", None
    text = f"Zähler {before if before is not None else '?'} → {after if after is not None else '?'}"
    if before is None or after is None:
        return text, "Zähler konnte nicht gelesen werden"
    if after <= before:
        return text, f"Zähler nicht gestiegen ({before} → {after})"
    return text, None
