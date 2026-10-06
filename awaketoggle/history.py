"""Verlauf des Power-Coins-Zählers: CSV speichern, aktuellen Wert merken, HTML-Ansicht (Tabelle + Diagramm)."""
import csv
import html
import logging
import os
import threading
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

HEADER = ("Zeit", "Wert", "Änderung")
CHART_POINTS = 500
TABLE_ROWS = 300
REFRESH_S = 30


class CoinHistory:
    def __init__(self, csv_path, html_path=None, now=datetime.now):
        self.csv_path = Path(csv_path)
        self.html_path = Path(html_path) if html_path else self.csv_path.with_suffix(".html")
        self.on_change = None
        self._now = now
        self._lock = threading.Lock()
        self.start = None
        self.last = None
        self.last_time = ""
        rows = self.rows()
        if rows:
            self.last_time, self.last = rows[-1][0], rows[-1][1]

    def rows(self) -> list:
        """[(Zeit, Wert, Änderung)] aus der CSV, älteste zuerst; unlesbare Zeilen werden übersprungen."""
        if not self.csv_path.exists():
            return []
        out = []
        with open(self.csv_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f, delimiter=";"):
                try:
                    out.append((row[0], int(row[1]), int(row[2] or 0)))
                except (IndexError, ValueError):
                    continue
        return out

    def record(self, value):
        """Gelesenen Wert speichern (None = nicht gelesen, wird ignoriert) und Ansicht aktualisieren."""
        if value is None:
            return None
        value = int(value)
        with self._lock:
            diff = value - self.last if self.last is not None else 0
            if self.start is None:
                self.start = value
            self.last, self.last_time = value, self._now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                self.csv_path.parent.mkdir(parents=True, exist_ok=True)
                new = not self.csv_path.exists()
                with open(self.csv_path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
                    w = csv.writer(f, delimiter=";")
                    if new:
                        w.writerow(HEADER)
                    w.writerow((self.last_time, value, diff))
                self.write_html()
            except OSError:
                log.exception("Zähler-Verlauf konnte nicht gespeichert werden")
        log.info("Power Coins: %s (%+d)", value, diff)
        if self.on_change:
            self.on_change()
        return value

    def label(self) -> str:
        if self.last is None:
            return "Power Coins: noch nicht gelesen"
        text = f"Power Coins: {self.last}"
        if self.start is not None:
            text += f" ({self.last - self.start:+d} seit Programmstart)"
        return text

    def write_html(self) -> Path:
        self.html_path.write_text(render_html(self.rows(), self.csv_path), "utf-8")
        return self.html_path

    def open_view(self) -> None:
        os.startfile(str(self.write_html()))  # noqa: S606 – nur unter Windows


def _chart(rows) -> str:
    pts = rows[-CHART_POINTS:]
    if len(pts) < 2:
        return '<p class="muted">Diagramm erscheint ab zwei Messwerten.</p>'
    w, h, pad = 960, 280, 40
    lo, hi = min(p[1] for p in pts), max(p[1] for p in pts)
    span = (hi - lo) or 1
    xy = [(pad + i * (w - 2 * pad) / (len(pts) - 1), h - pad - (p[1] - lo) * (h - 2 * pad) / span)
          for i, p in enumerate(pts)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5"><title>{html.escape(p[0])}: {p[1]}</title></circle>'
                   for (x, y), p in zip(xy, pts))
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Verlauf Power Coins">'
            f'<line x1="{pad}" y1="{h - pad}" x2="{w - pad}" y2="{h - pad}" class="axis"/>'
            f'<text x="{pad}" y="{pad - 12}" class="lbl">{hi}</text>'
            f'<text x="{pad}" y="{h - pad + 22}" class="lbl">{lo} · {html.escape(pts[0][0])}</text>'
            f'<text x="{w - pad}" y="{h - pad + 22}" class="lbl" text-anchor="end">{html.escape(pts[-1][0])}</text>'
            f'<polyline points="{line}"/>{dots}</svg>')


def render_html(rows, csv_path) -> str:
    last = rows[-1][1] if rows else "–"
    gain = rows[-1][1] - rows[0][1] if rows else 0
    today = datetime.now().strftime("%Y-%m-%d")
    today_rows = [r for r in rows if r[0].startswith(today)]
    gain_today = today_rows[-1][1] - today_rows[0][1] if today_rows else 0
    body = "".join(f"<tr><td>{html.escape(t)}</td><td>{v}</td>"
                   f"<td class=\"{'up' if d > 0 else 'down' if d < 0 else ''}\">{d:+d}</td></tr>"
                   for t, v, d in reversed(rows[-TABLE_ROWS:]))
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="{REFRESH_S}"><title>Power Coins: {last} – AwakeToggle</title>
<style>
body{{margin:0;padding:32px 40px;background:#140d24;color:#eee8ff;font-family:Segoe UI,sans-serif}}
h1{{margin:0 0 4px;font-weight:600}} .muted{{color:#a99bd0}}
.cards{{display:flex;gap:16px;margin:24px 0}}
.card{{border:1px solid #6b3fd6;border-radius:12px;padding:16px 22px;background:#1e1438;min-width:170px}}
.card b{{display:block;font-size:34px;margin-top:4px}}
svg{{width:100%;max-width:960px;background:#1e1438;border-radius:12px}}
polyline{{fill:none;stroke:#c86bff;stroke-width:2.5}} circle{{fill:#ff5fa2}}
.axis{{stroke:#4a3a78}} .lbl{{fill:#a99bd0;font-size:13px}}
table{{border-collapse:collapse;margin-top:24px;min-width:420px}}
td,th{{padding:6px 14px;border-bottom:1px solid #2e2250;text-align:left}}
.up{{color:#5fe39a}} .down{{color:#ff6b6b}} a{{color:#c86bff}}
</style></head><body>
<h1>Power Coins – Verlauf</h1>
<div class="muted">Aktualisiert sich alle {REFRESH_S} s · Daten: <a href="{Path(csv_path).as_uri()}">{html.escape(Path(csv_path).name)}</a></div>
<div class="cards">
<div class="card">Aktuell<b id="coins-current">{last}</b></div>
<div class="card">Heute<b>{gain_today:+d}</b></div>
<div class="card">Gesamt<b>{gain:+d}</b></div>
<div class="card">Messungen<b>{len(rows)}</b></div>
</div>
{_chart(rows)}
<table><thead><tr><th>Zeit</th><th>Wert</th><th>Änderung</th></tr></thead><tbody>{body}</tbody></table>
</body></html>
"""
