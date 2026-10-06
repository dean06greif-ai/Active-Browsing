"""Verlauf des Power-Coins-Zählers: wann ablesen, CSV mit Uhrzeit + Sitzungsdaten, HTML-Ansicht (Tabelle + Diagramm)."""
import csv
import html
import logging
import os
import random
import threading
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

HEADER = ("Zeit", "Wert", "Änderung", "Minuten seit letzter Messung", "Sitzungen seit letzter Messung",
          "Aktionen", "Sitzungsdauer (s)", "Modus", "Status", "Wochentag")
WEEKDAYS = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
TIME_FMT = "%Y-%m-%d %H:%M:%S"
CHART_POINTS = 500
TABLE_ROWS = 300
REFRESH_S = 30


def mode_label(mode: str, percent: int) -> str:
    return {"off": "aus", "session": "jede Sitzung"}.get(mode, f"zufällig ca. {percent} %")


class CoinHistory:
    def __init__(self, csv_path, html_path=None, now=datetime.now, rng=None):
        self.csv_path = Path(csv_path)
        self.html_path = Path(html_path) if html_path else self.csv_path.with_suffix(".html")
        self.on_change = None
        self._now = now
        self._rng = rng or random.Random()
        self._lock = threading.Lock()
        self.start = None
        self.last = None
        self.last_time = ""
        self.sessions = 0  # fertige Sitzungen seit dem letzten Ablesen
        self._migrate()
        rows = self.rows()
        if rows:
            self.last_time, self.last = rows[-1][0], rows[-1][1]

    # ---------- wann ablesen ----------

    def want(self, cfg) -> bool:
        """Diese Sitzung am Ende ablesen? off = nie, session = immer, random = in ca. badge_random_percent %."""
        if cfg.badge_mode == "off":
            return False
        if cfg.badge_mode == "session":
            return True
        return self._rng.random() * 100 < cfg.badge_random_percent

    def session_done(self, result, cfg) -> None:
        """Nach jeder Sitzung: zählen und, falls abgelesen wurde, mit Sitzungsdaten speichern."""
        if result.status != "done":
            return
        self.sessions += 1
        if not result.badge_read:
            log.info("Zähler diesmal nicht abgelesen (%s, %d Sitzung(en) seit letzter Messung)",
                     mode_label(cfg.badge_mode, cfg.badge_random_percent), self.sessions)
            return
        self.record(result.badge, sessions=self.sessions, actions=max(result.actions - 2, 0),
                    seconds=round(result.seconds), mode=mode_label(cfg.badge_mode, cfg.badge_random_percent))
        self.sessions = 0

    # ---------- Datei ----------

    def _migrate(self) -> None:
        """Ältere CSV (weniger Spalten) auf die aktuelle Kopfzeile bringen; vorhandene Werte bleiben."""
        if not self.csv_path.exists():
            return
        rows = self.records(raw=True)
        if rows and tuple(rows[0]) == HEADER:
            return
        body = [r + [""] * (len(HEADER) - len(r)) for r in rows if r and r[0] != "Zeit"]
        try:
            self._write_all(body)
        except OSError:
            log.exception("Zähler-Verlauf konnte nicht umgestellt werden")

    def _write_all(self, body) -> None:
        tmp = self.csv_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(HEADER)
            w.writerows(body)
        os.replace(tmp, self.csv_path)

    def records(self, raw=False) -> list:
        """Alle Zeilen als Listen (auch „nicht lesbar“), älteste zuerst; raw=True inkl. Kopfzeile."""
        if not self.csv_path.exists():
            return []
        with open(self.csv_path, encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.reader(f, delimiter=";") if r]
        return rows if raw else [r + [""] * (len(HEADER) - len(r)) for r in rows if r[0] != "Zeit"]

    def rows(self) -> list:
        """[(Zeit, Wert, Änderung)] nur gelesene Werte, älteste zuerst."""
        out = []
        for r in self.records():
            try:
                out.append((r[0], int(r[1]), int(r[2] or 0)))
            except ValueError:
                continue
        return out

    def record(self, value, sessions="", actions="", seconds="", mode=""):
        """Ablesung speichern; value None = nicht lesbar (Zeile mit Status, Wert bleibt). Gibt value zurück."""
        now = self._now()
        with self._lock:
            minutes = ""
            if self.last_time:
                try:
                    minutes = round((now - datetime.strptime(self.last_time, TIME_FMT)).total_seconds() / 60, 1)
                except ValueError:
                    pass
            if value is None:
                row = (now.strftime(TIME_FMT), "", "", minutes, sessions, actions, seconds, mode, "nicht lesbar",
                       WEEKDAYS[now.weekday()])
            else:
                value = int(value)
                diff = value - self.last if self.last is not None else 0
                status = "erste Messung" if self.last is None else "gestiegen" if diff > 0 else "nicht gestiegen"
                if self.start is None:
                    self.start = value
                self.last, self.last_time = value, now.strftime(TIME_FMT)
                row = (self.last_time, value, diff, minutes, sessions, actions, seconds, mode, status,
                       WEEKDAYS[now.weekday()])
            try:
                self.csv_path.parent.mkdir(parents=True, exist_ok=True)
                new = not self.csv_path.exists()
                with open(self.csv_path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
                    w = csv.writer(f, delimiter=";")
                    if new:
                        w.writerow(HEADER)
                    w.writerow(row)
                self.write_html(now)
            except OSError:
                log.exception("Zähler-Verlauf konnte nicht gespeichert werden")
        log.info("Power Coins: %s (%s)", value if value is not None else "nicht lesbar", row[8])
        if value is not None and self.on_change:
            self.on_change()
        return value

    def label(self) -> str:
        if self.last is None:
            return "Power Coins: noch nicht gelesen"
        text = f"Power Coins: {self.last}"
        if self.start is not None:
            text += f" ({self.last - self.start:+d} seit Programmstart)"
        return text

    def write_html(self, now=None) -> Path:
        self.html_path.write_text(render_html(self.records(), self.csv_path, now), "utf-8")
        return self.html_path

    def open_view(self) -> None:
        os.startfile(str(self.write_html()))  # noqa: S606 – nur unter Windows


def _valid(records) -> list:
    out = []
    for r in records:
        try:
            out.append((r[0], int(r[1])))
        except ValueError:
            continue
    return out


def _chart(pts) -> str:
    pts = pts[-CHART_POINTS:]
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


def _per_hour(pts) -> str:
    if len(pts) < 2:
        return "–"
    try:
        first, last = (datetime.strptime(p[0], TIME_FMT) for p in (pts[0], pts[-1]))
        hours = (last - first).total_seconds() / 3600
    except ValueError:
        return "–"
    return f"{(pts[-1][1] - pts[0][1]) / hours:+.1f}" if hours > 0 else "–"


def _cell(i, v) -> str:
    cls = ""
    if i == 2 and v not in ("", "0"):
        cls = ' class="down"' if v.startswith("-") else ' class="up"'
        v = v if v.startswith("-") else f"+{v}"
    elif i == 8 and v == "nicht lesbar":
        cls = ' class="down"'
    return f"<td{cls}>{html.escape(v)}</td>"


def render_html(records, csv_path, now=None) -> str:
    pts = _valid(records)
    now = now or datetime.now()
    last = pts[-1][1] if pts else "–"
    gain = pts[-1][1] - pts[0][1] if pts else 0
    today = [p for p in pts if p[0].startswith(now.strftime("%Y-%m-%d"))]
    gain_today = today[-1][1] - today[0][1] if today else 0
    failed = sum(1 for r in records if r[8] == "nicht lesbar")
    head = "".join(f"<th>{html.escape(h)}</th>" for h in HEADER)
    body = "".join("<tr>" + "".join(_cell(i, v) for i, v in enumerate(r[:len(HEADER)])) + "</tr>"
                   for r in reversed(records[-TABLE_ROWS:]))
    csv_link = f'<a href="{Path(csv_path).as_uri()}">{html.escape(Path(csv_path).name)}</a>'
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="{REFRESH_S}"><title>Power Coins: {last} – AwakeToggle</title>
<style>
body{{margin:0;padding:32px 40px;background:#140d24;color:#eee8ff;font-family:Segoe UI,sans-serif}}
h1{{margin:0 0 4px;font-weight:600}} .muted{{color:#a99bd0}}
.cards{{display:flex;flex-wrap:wrap;gap:16px;margin:24px 0}}
.card{{border:1px solid #6b3fd6;border-radius:12px;padding:16px 22px;background:#1e1438;min-width:150px}}
.card b{{display:block;font-size:34px;margin-top:4px}}
svg{{width:100%;max-width:960px;background:#1e1438;border-radius:12px}}
polyline{{fill:none;stroke:#c86bff;stroke-width:2.5}} circle{{fill:#ff5fa2}}
.axis{{stroke:#4a3a78}} .lbl{{fill:#a99bd0;font-size:13px}}
table{{border-collapse:collapse;margin-top:24px;font-size:14px}}
td,th{{padding:6px 12px;border-bottom:1px solid #2e2250;text-align:left;white-space:nowrap}}
th{{color:#a99bd0;font-weight:500}} .up{{color:#5fe39a}} .down{{color:#ff6b6b}} a{{color:#c86bff}}
</style></head><body>
<h1>Power Coins – Verlauf</h1>
<div class="muted">Aktualisiert sich alle {REFRESH_S} s · Daten zum Auswerten (Excel): {csv_link}</div>
<div class="cards">
<div class="card">Aktuell<b id="coins-current">{last}</b></div>
<div class="card">Heute<b>{gain_today:+d}</b></div>
<div class="card">Gesamt<b>{gain:+d}</b></div>
<div class="card">Ø pro Stunde<b>{_per_hour(pts)}</b></div>
<div class="card">Messungen<b>{len(pts)}</b></div>
<div class="card">Nicht lesbar<b>{failed}</b></div>
</div>
{_chart(pts)}
<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
</body></html>
"""
