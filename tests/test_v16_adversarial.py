"""Zusätzliche Adversarial-Tests für v1.6.0: Updater-Edgecases, Persona-Verteilung, Consent-Edgecases."""
import io
import json
import random
import urllib.error
import zipfile
from pathlib import Path

import pytest

from awaketoggle import personas, updater
from awaketoggle.consent import accept_rank, choose, decline_rank


# ---------- Updater ----------

def _get_factory(branches_pages, versions, zips=None):
    def get(url, timeout=None):
        if "api.github.com" in url:
            page = int(url.rsplit("page=", 1)[1])
            data = branches_pages.get(page, [])
            return json.dumps([{"name": b} for b in data]).encode()
        if "raw.githubusercontent.com" in url:
            # URL-Form: https://raw.githubusercontent.com/<repo>/<branch>/awaketoggle/__init__.py
            tail = url.split("raw.githubusercontent.com/", 1)[1]
            branch = tail.split("/", 2)[2].rsplit("/awaketoggle/", 1)[0]
            if branch not in versions:
                raise urllib.error.HTTPError(url, 404, "nf", {}, None)
            return f'__version__ = "{versions[branch]}"\n'.encode()
        if url.endswith(".zip") and zips:
            return zips[url]
        raise AssertionError(url)
    return get


def test_list_branches_paginates():
    pages = {1: [f"b{i}" for i in range(100)], 2: ["last"]}
    branches = updater.list_branches("x/y", _get_factory(pages, {}))
    assert len(branches) == 101 and branches[-1] == "last"


def test_find_update_returns_none_when_all_versions_equal_or_lower():
    get = _get_factory({1: ["main", "old"]}, {"main": "1.6.0", "old": "1.5.9"})
    assert updater.find_update("x/y", "1.6.0", get) is None


def test_find_update_handles_unreadable_version_branches():
    # kaputt kommt im 404 raus -> leere Version -> wird ignoriert
    get = _get_factory({1: ["main", "kaputt", "neu"]}, {"main": "1.6.0", "neu": "1.8.0"})
    up = updater.find_update("x/y", "1.6.0", get)
    assert up == updater.Update("neu", "1.8.0")


def test_parse_version_edge_cases():
    assert updater.parse_version("1.6.0") == (1, 6, 0)
    assert updater.parse_version("v2.0.0-rc1") == (2, 0, 0, 1)
    assert updater.parse_version("abc") == ()
    assert updater.parse_version(None) == ()
    # tuple length-truncated to 4 numbers
    assert updater.parse_version("1.2.3.4.5.6") == (1, 2, 3, 4)


def test_download_sanitizes_target_folder_name(tmp_path):
    up = updater.Update("feature/foo bar!", "1.9.0")
    url = updater.ZIP_URL.format(repo="a/b", branch="feature/foo%20bar%21")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("root/Installieren.cmd", "@echo off")
        z.writestr("root/awaketoggle/__init__.py", '__version__ = "1.9.0"')
    folder = updater.download("a/b", up, tmp_path, _get_factory({}, {}, {url: buf.getvalue()}))
    # Keine Sonderzeichen in Ordnernamen, Version + Branch erkennbar
    assert folder.exists() and folder.parent == tmp_path
    assert "/" not in folder.name and " " not in folder.name and "!" not in folder.name
    assert folder.name.startswith("v1.9.0_")


def test_download_cleans_only_folders_not_running_app(tmp_path, monkeypatch):
    # simuliere laufende App unter tmp_path/running
    running = tmp_path / "running"
    (running / "awaketoggle").mkdir(parents=True)
    monkeypatch.setattr(updater, "__file__", str(running / "awaketoggle" / "updater.py"))
    (tmp_path / "v1.0.0_alt").mkdir()
    up = updater.Update("neu", "1.9.0")
    url = updater.ZIP_URL.format(repo="a/b", branch="neu")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("root/Installieren.cmd", "@echo off")
        z.writestr("root/awaketoggle/__init__.py", '__version__ = "1.9.0"')
    folder = updater.download("a/b", up, tmp_path, _get_factory({}, {}, {url: buf.getvalue()}))
    names = {p.name for p in tmp_path.iterdir()}
    assert folder.name in names and "running" in names and "v1.0.0_alt" not in names


def test_describe_covers_generic_exceptions():
    assert "Abfragelimit" in updater.describe(urllib.error.HTTPError("u", 429, "x", {}, None))
    assert "500" in updater.describe(urllib.error.HTTPError("u", 500, "x", {}, None))
    assert updater.describe(RuntimeError("boom")) == "boom"
    assert updater.describe(ValueError()) == "ValueError"


# ---------- Personas ----------

def test_rotation_covers_all_personas_evenly():
    rot = personas.Rotation()
    rng = random.Random(42)
    counts = {}
    for _ in range(1300):
        p = rot.next(rng)
        counts[p.name] = counts.get(p.name, 0) + 1
    assert set(counts) == {p.name for p in personas.PERSONAS}
    # jede Persona ungefähr gleich oft (±50%)
    expected = 1300 / len(personas.PERSONAS)
    for name, c in counts.items():
        assert 0.5 * expected <= c <= 1.5 * expected, (name, c)


def test_persona_sites_look_like_domain_words():
    for p in personas.PERSONAS:
        for s in p.sites:
            assert s and s.lower() == s and "." not in s and " " not in s, (p.name, s)


# ---------- Consent ----------

def test_accept_rank_rejects_long_and_negative_names():
    assert accept_rank("x" * 60) is None
    assert accept_rank("") is None
    assert accept_rank("Nicht akzeptieren") is None  # „nicht" ist NEGATIVE
    assert accept_rank("Alle akzeptieren") == 0
    assert accept_rank("OK") == 2


def test_choose_prefers_strong_accept_over_weak():
    banner = [("OK", (0, 100, 50, 120)), ("Alle akzeptieren", (60, 100, 160, 120))]
    assert choose(banner)[1] == "Alle akzeptieren"


def test_choose_decline_only_if_in_same_banner_vertically():
    # ein echter Zustimmen-Button auf y=100, aber Ablehnen weit weg (y=1000) -> keine Ablehnung
    far = [("Alle akzeptieren", (0, 100, 100, 120)), ("Ablehnen", (0, 1000, 100, 1020))]
    assert choose(far, decline=True)[0] == "accept"
    # beide nah beieinander -> Ablehnung möglich
    near = [("Alle akzeptieren", (0, 100, 100, 120)), ("Ablehnen", (120, 100, 220, 120))]
    assert choose(near, decline=True)[0] == "decline"


def test_decline_rank_ignores_management_links():
    assert decline_rank("Einstellungen verwalten") is None
    assert decline_rank("Mehr Optionen") is None
    assert decline_rank("Partner anzeigen") is None
    assert decline_rank("Alle ablehnen") == 0
