"""Nach Update suchen: neueste Version auf GitHub finden, herunterladen und mit Installieren.cmd installieren.

Neue Versionen liegen meist auf neuen Branches. Darum wird auf allen Branches die Versionsnummer aus
awaketoggle/__init__.py gelesen; der Branch mit der höchsten Version (höher als die laufende) gewinnt.
Netzwerk wird nur benutzt, wenn Sie im Tray-Menü „Nach Update suchen“ anklicken.
"""
import io
import json
import logging
import re
import shutil
import subprocess
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from . import __version__

log = logging.getLogger(__name__)

BRANCHES_URL = "https://api.github.com/repos/{repo}/branches?per_page=100&page={page}"
VERSION_URL = "https://raw.githubusercontent.com/{repo}/{branch}/awaketoggle/__init__.py"
ZIP_URL = "https://github.com/{repo}/archive/refs/heads/{branch}.zip"
VERSION_RE = re.compile(r"""__version__\s*=\s*["']([^"']+)["']""")
TIMEOUT_S = 15
ZIP_TIMEOUT_S = 180
MAX_PAGES = 5
WORKERS = 8
INSTALLER = "Installieren.cmd"
CREATE_NEW_CONSOLE = 0x00000010


@dataclass(frozen=True)
class Update:
    branch: str
    version: str


def parse_version(text: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", text or "")[:4])


def _get(url: str, timeout: float = TIMEOUT_S) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "AwakeToggle-Updater",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _path(branch: str) -> str:
    return quote(branch, safe="/")


def list_branches(repo: str, get=_get) -> list:
    names = []
    for page in range(1, MAX_PAGES + 1):
        data = json.loads(get(BRANCHES_URL.format(repo=repo, page=page)))
        names += [b["name"] for b in data]
        if len(data) < 100:
            break
    return names


def branch_version(repo: str, branch: str, get=_get) -> str:
    try:
        text = get(VERSION_URL.format(repo=repo, branch=_path(branch))).decode("utf-8", "replace")
    except Exception:
        log.debug("Version auf Branch %s nicht lesbar", branch, exc_info=True)
        return ""
    m = VERSION_RE.search(text)
    return m.group(1) if m else ""


def find_update(repo: str, current: str = __version__, get=_get):
    """Branch mit der höchsten Version, falls höher als die laufende; sonst None."""
    branches = list_branches(repo, get)
    with ThreadPoolExecutor(WORKERS) as ex:
        versions = list(ex.map(lambda b: branch_version(repo, b, get), branches))
    log.info("Update-Suche: %d Branches, Versionen %s", len(branches),
             ", ".join(f"{b}={v or '-'}" for b, v in zip(branches, versions)))
    best, best_v = None, parse_version(current) or (0,)
    for branch, version in zip(branches, versions):
        v = parse_version(version)
        if v and v > best_v:
            best, best_v = Update(branch, version), v
    return best


def download(repo: str, update: Update, base: Path, get=_get) -> Path:
    """Branch als ZIP laden und nach base/<version>_<branch> entpacken; liefert den Ordner mit Installieren.cmd."""
    data = get(ZIP_URL.format(repo=repo, branch=_path(update.branch)), ZIP_TIMEOUT_S)
    target = base / re.sub(r"[^A-Za-z0-9_.-]+", "_", f"v{update.version}_{update.branch}")
    tmp = target.with_name(target.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(tmp)
    found = [p for p in tmp.rglob(INSTALLER) if (p.parent / "awaketoggle" / "__init__.py").exists()]
    if not found:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"{INSTALLER} fehlt im Download von Branch {update.branch}")
    shutil.rmtree(target, ignore_errors=True)
    shutil.move(str(min(found, key=lambda p: len(p.parts)).parent), str(target))
    shutil.rmtree(tmp, ignore_errors=True)
    _cleanup(base, keep=target)
    return target


def _cleanup(base: Path, keep: Path) -> None:
    """Ältere Update-Ordner löschen – außer dem, aus dem das Programm gerade selbst läuft."""
    running = Path(__file__).resolve().parent.parent
    for p in base.iterdir():
        if p.is_dir() and p != keep and p.resolve() != running:
            shutil.rmtree(p, ignore_errors=True)


def start_install(folder: Path) -> None:
    """Installieren.cmd in einem eigenen Fenster starten; es beendet AwakeToggle, installiert und startet neu."""
    subprocess.Popen(["cmd.exe", "/c", str(folder / INSTALLER)], cwd=str(folder), creationflags=CREATE_NEW_CONSOLE)


def describe(e: Exception) -> str:
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (403, 429):
            return "GitHub-Abfragelimit erreicht – bitte in einer Stunde erneut versuchen"
        if e.code == 404:
            return "Repository nicht gefunden (update_repo in der Konfiguration prüfen)"
        return f"GitHub antwortet mit Fehler {e.code}"
    if isinstance(e, urllib.error.URLError):
        return "keine Verbindung zu GitHub (Internet prüfen)"
    return str(e) or type(e).__name__
