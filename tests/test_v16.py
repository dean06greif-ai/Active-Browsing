"""v1.6.0: Update-Suche, Browsing-Persönlichkeiten, Tab-Aufräumen, natürlichere Cookie-Hinweise."""
import io
import json
import random
import urllib.error
import zipfile

from awaketoggle import personas, queries, updater
from awaketoggle.browse import (ACTIONS, MAX_RARE, MAX_TABS, RARE, REPEAT_OK, TAB_LIMIT, Builder, Model, Person,
                                _new_window, make_scenario)
from awaketoggle.browse_runner import Runner
from awaketoggle.config import Config, load
from awaketoggle.consent import accept_rank, choose, decline_rank
from tests.test_browse import NAMES, USER, FakeDesk

NEW_THEMES = ("gaming", "sport", "musik", "filme", "fitness", "mode", "heimwerken", "familie", "nachrichten",
              "wissenschaft", "fernreisen")


# ---------- Themen und Persönlichkeiten ----------

def test_new_themes_exist_and_have_weights():
    assert len(queries.THEMES) >= 30
    assert set(queries.THEMES) == set(queries.THEME_WEIGHTS)
    for t in NEW_THEMES:
        starts, refines, related = queries.THEMES[t]
        assert len(starts) >= 5 and refines and related


def test_personas_reference_known_themes_and_are_distinct():
    assert len(personas.PERSONAS) >= 10
    assert len({p.name for p in personas.PERSONAS}) == len(personas.PERSONAS)
    for p in personas.PERSONAS:
        assert set(p.themes) <= set(queries.THEMES), p.name
        assert 0 <= p.decline < 0.5, p.name  # meistens akzeptieren
        assert len(p.styles) == 3 and set(p.weights) == set(queries.THEME_WEIGHTS)


def test_personas_rotate_without_quick_repeats():
    rot = personas.Rotation()
    rng = random.Random(1)
    names = [rot.next(rng).name for _ in range(300)]
    for i in range(3, len(names)):
        assert names[i] not in names[i - 3:i], (i, names[i - 3:i + 1])
    assert set(names) == {p.name for p in personas.PERSONAS}


def test_persona_mostly_searches_its_favorite_themes():
    gamer = next(p for p in personas.PERSONAS if p.name == "Gamer")
    rng = random.Random(5)
    themes = [queries.Interest(rng, weights=gamer.weights).theme for _ in range(2000)]
    share = sum(t in gamer.themes for t in themes) / len(themes)
    assert 0.5 < share < 0.9
    assert len(set(themes)) > 15  # trotzdem bunt gemischt


def test_scenario_label_names_the_persona():
    labels = {make_scenario(Config(signal="browse"), random.Random(s)).label for s in range(40)}
    assert any("Gamer" in lb or "Hobbykoch" in lb or "Sportfan" in lb for lb in labels)
    assert all(lb.startswith("Browser-Test (") for lb in labels)


# ---------- Eigene Tabs aufräumen ----------

def _simulate(seed, n=80):
    rng = random.Random(seed)
    persona = personas.PERSONAS[seed % len(personas.PERSONAS)]
    b = Builder(rng, "normal", True, persona.decline)
    m = Model(person=Person.random(rng, persona))
    _new_window(b, m, rng)
    last, ways = None, []
    for _ in range(n):
        ids, weights = [], []
        for aid, (weight, _) in ACTIONS.items():
            if aid in RARE and (aid in m.used or len(m.used & RARE) >= MAX_RARE):
                continue
            w = weight(m)
            if w > 0:
                ids.append(aid)
                weights.append(w * (1.0 if aid != last else 0.6 if aid in REPEAT_OK else 0.2))
        aid = rng.choices(ids, weights)[0]
        before = m.last_tidy
        ACTIONS[aid][1](b, m, rng)
        if m.last_tidy != before or aid == "alte_tabs_schliessen":
            ways.append(m.last_tidy)
        for w in m.wins:
            assert TAB_LIMIT[0] <= w.limit <= TAB_LIMIT[1]
            assert 1 <= w.tabs <= w.limit + 1 <= MAX_TABS, (seed, aid, w.tabs, w.limit)
        m.used.add(aid)
        last = aid
    return ways, b.take()


def test_own_tabs_stay_near_random_limit_and_are_closed_in_varied_ways():
    all_ways, keys = [], set()
    for seed in range(300):
        ways, steps = _simulate(seed)
        all_ways += ways
        keys |= {s[1] for s in steps if s[0] == "key"}
        for a, b in zip(ways, ways[1:]):
            assert a != b, (seed, ways)  # nie zweimal hintereinander auf dieselbe Art
    assert set(all_ways) == {"aelteste", "aktuelle", "durchblaettern"}
    assert {"ctrl+1", "ctrl+w", "ctrl+f4"} <= keys


def test_long_runs_close_old_tabs_but_never_user_tabs():
    closed_old = 0
    for seed in range(40):
        desk = FakeDesk()
        cfg = Config(signal="browse", browse_actions_max=80)
        plan = make_scenario(cfg, random.Random(seed))
        closed_old += sum(n == "alte_tabs_schliessen" for n, _ in plan.steps)
        runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(seed))
        peak = 0
        orig = desk.send_combo

        def watch(vks, orig=orig):
            nonlocal peak
            orig(vks)
            peak = max([peak] + [w["tabs"] for h, w in desk.wins.items() if h != USER])
        desk.send_combo = watch
        res = runner.run(plan, ())
        assert res.status == "done", (seed, res)
        assert set(desk.wins) == {USER} and desk.wins[USER]["tabs"] == 3
        assert [k for h, k in desk.sent if h == USER] == ["ctrl+n"]
        assert peak <= MAX_TABS + 1  # +1: Quelltext-Tab (Strg+U) kurzzeitig
    assert closed_old > 20


def test_leftover_window_is_closed_even_if_its_page_finished_loading_after_abort():
    desk = FakeDesk(user_input_at_ms=1_000_000 + 4_000)
    orig_sleep = desk.sleep
    loaded = []

    def sleep(s):
        orig_sleep(s)
        if not loaded and desk.ms >= desk.user_input_at + 1_500:
            for h, w in desk.wins.items():
                if h != USER:
                    w["title"] = "Seite fertig geladen"
            loaded.append(True)
    desk.sleep = sleep
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(5))
    res = runner.run(make_scenario(Config(signal="browse"), random.Random(5)), ())
    assert res.status == "aborted" and runner.leftover and loaded
    assert all(t == "Seite fertig geladen" for _, t in runner.leftover)
    desk.user_input_at = None
    desk.activate(USER)
    res = runner.run(make_scenario(Config(signal="browse"), random.Random(9)), ())
    assert res.status == "done" and set(desk.wins) == {USER}


# ---------- Cookie-/Datenschutz-Hinweise ----------

def test_decline_rank_and_choose():
    for yes in ("Alle ablehnen", "Ablehnen", "Nur notwendige Cookies", "Reject all", "Nur erforderliche",
                "Weiter ohne Zustimmung", "Only necessary"):
        assert decline_rank(yes) is not None, yes
    for no in ("Einstellungen", "Mehr Optionen", "Alle akzeptieren", "Partner verwalten", "Pur-Abo abschließen",
               "Benachrichtigungen ablehnen", ""):
        assert decline_rank(no) is None, no
    assert accept_rank("Akzeptieren und weiterlesen") == 1 and accept_rank("Tout accepter") == 0
    banner = [("Einstellungen", (0, 500, 80, 530)), ("Alle akzeptieren", (100, 500, 200, 530)),
              ("Nur notwendige", (220, 500, 320, 530))]
    assert choose(banner) == ("accept", "Alle akzeptieren", (100, 500, 200, 530))
    assert choose(banner, decline=True) == ("decline", "Nur notwendige", (220, 500, 320, 530))
    assert choose([("Ablehnen", (0, 0, 50, 20))], decline=True) is None  # ohne Zustimmen-Button kein Hinweis
    far = [("Alle akzeptieren", (100, 100, 200, 130)), ("Ablehnen", (100, 900, 200, 930))]
    assert choose(far, decline=True)[0] == "accept"


def _banner_desk(seed, delay_ms=0, sticky=False):
    desk = FakeDesk()
    orig = desk.send_combo
    orig_find = desk.find_consent
    shown = {}

    def nav(vks):
        orig(vks)
        fg = desk.foreground()
        if fg != USER and NAMES[vks[-1]] == "enter" and fg in desk.wins:
            desk.wins[fg].update(banner="Alle akzeptieren", banner_decline="Nur notwendige", sticky=sticky)
            shown[fg] = desk.ms + delay_ms

    def find(h, decline=False):
        return orig_find(h, decline) if desk.ms >= shown.get(h, 0) else None
    desk.send_combo, desk.find_consent = nav, find
    return desk


def test_cookie_banners_are_mostly_accepted_sometimes_declined():
    kinds = []
    for seed in range(40):
        desk = _banner_desk(seed)
        runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(seed))
        persona = personas.PERSONAS[seed % len(personas.PERSONAS)]
        res = runner.run(make_scenario(Config(signal="browse"), random.Random(seed), persona), ())
        assert res.status == "done", (seed, res)
        kinds += [name for _, name in desk.accepted]
    yes, no = kinds.count("Alle akzeptieren"), kinds.count("Nur notwendige")
    assert yes > no > 0 and yes > 3 * no


def test_late_cookie_banner_is_still_found():
    total = 0
    for seed in range(15):
        desk = _banner_desk(seed, delay_ms=1_000)
        runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(seed))
        res = runner.run(make_scenario(Config(signal="browse"), random.Random(seed)), ())
        assert res.status == "done", (seed, res)
        total += len(desk.accepted)
    assert total > 10


def test_stuck_cookie_banner_is_tried_twice_then_left_alone():
    desk = _banner_desk(3, sticky=True)
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(3))
    persona = personas.PERSONAS[0]
    res = runner.run(make_scenario(Config(signal="browse"), random.Random(3), persona), ())
    assert res.status == "done"
    assert 1 <= len(desk.accepted) <= 2
    assert any("ließ sich nicht wegklicken" in p for p in res.problems)


# ---------- Update ----------

def _fake_github(branches, versions, zips=None):
    def get(url, timeout=None):
        if "api.github.com" in url:
            page = int(url.rsplit("page=", 1)[1])
            return json.dumps([{"name": b} for b in branches] if page == 1 else []).encode()
        if "raw.githubusercontent.com" in url:
            branch = url.split("/Active-Browsing/", 1)[1].rsplit("/awaketoggle/", 1)[0]
            if branch not in versions:
                raise urllib.error.HTTPError(url, 404, "nf", {}, None)
            return f'__version__ = "{versions[branch]}"\nAPP_NAME = "AwakeToggle"\n'.encode()
        if url.endswith(".zip"):
            return zips[url]
        raise AssertionError(url)
    return get


def test_parse_version():
    assert updater.parse_version("1.10.0") > updater.parse_version("1.9.3")
    assert updater.parse_version("v2.0") > updater.parse_version("1.99.9")
    assert updater.parse_version("") == ()


def test_find_update_picks_highest_newer_branch():
    repo = "dean06greif-ai/Active-Browsing"
    get = _fake_github(["main", "conflict_041026_2226", "neu_1", "kaputt"],
                       {"main": "1.2.0", "conflict_041026_2226": "1.5.0", "neu_1": "1.7.1"})
    up = updater.find_update(repo, "1.6.0", get)
    assert up == updater.Update("neu_1", "1.7.1")
    assert updater.find_update(repo, "1.7.1", get) is None
    assert updater.find_update(repo, "2.0.0", get) is None


def _zip(top, files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(f"{top}/{name}", text)
    return buf.getvalue()


def test_download_extracts_branch_and_cleans_old_updates(tmp_path):
    repo = "dean06greif-ai/Active-Browsing"
    up = updater.Update("neu/branch", "1.7.0")
    url = updater.ZIP_URL.format(repo=repo, branch="neu/branch")
    data = _zip("Active-Browsing-neu-branch", {"Installieren.cmd": "@echo off", "tools/installieren.ps1": "",
                                              "awaketoggle/__init__.py": '__version__ = "1.7.0"'})
    (tmp_path / "v1.5.0_alt").mkdir()
    folder = updater.download(repo, up, tmp_path, _fake_github([], {}, {url: data}))
    assert folder.name == "v1.7.0_neu_branch"
    assert (folder / "Installieren.cmd").exists() and (folder / "awaketoggle" / "__init__.py").exists()
    assert [p.name for p in tmp_path.iterdir()] == [folder.name]


def test_download_rejects_archive_without_installer(tmp_path):
    repo = "a/b"
    up = updater.Update("x", "9.0.0")
    url = updater.ZIP_URL.format(repo=repo, branch="x")
    data = _zip("b-x", {"README.md": "nichts"})
    try:
        updater.download(repo, up, tmp_path, _fake_github([], {}, {url: data}))
        raise AssertionError("hätte scheitern müssen")
    except RuntimeError as e:
        assert "Installieren.cmd" in str(e)
    assert list(tmp_path.iterdir()) == []


def test_update_error_texts():
    assert "Abfragelimit" in updater.describe(urllib.error.HTTPError("u", 403, "x", {}, None))
    assert "nicht gefunden" in updater.describe(urllib.error.HTTPError("u", 404, "x", {}, None))
    assert "Verbindung" in updater.describe(urllib.error.URLError("offline"))


def test_config_update_repo(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"update_repo": " ich/mein-repo "}), "utf-8")
    cfg, warnings = load(p)
    assert cfg.update_repo == "ich/mein-repo" and warnings == []
    p.write_text(json.dumps({"update_repo": "https://github.com/x"}), "utf-8")
    cfg, warnings = load(p)
    assert cfg.update_repo == Config().update_repo and len(warnings) == 1


def test_consent_win_searches_largest_document_with_cached_properties(monkeypatch):
    import sys
    import types
    from awaketoggle import consent_win

    def rect(l, t, r, b):
        return types.SimpleNamespace(left=l, top=t, right=r, bottom=b)

    def el(name, r, off=False, enabled=True):
        return types.SimpleNamespace(CachedName=name, CachedBoundingRectangle=r, CachedIsOffscreen=off,
                                     CachedIsEnabled=enabled)

    class Found(list):
        Length = property(len)

        def GetElement(self, i):
            return self[i]

    class Doc:
        def __init__(self, r, buttons=(), texts=()):
            self.CachedBoundingRectangle, self.CachedIsOffscreen = r, False
            self.buttons, self.texts = buttons, texts

        def FindAllBuildCache(self, scope, cond, cr):
            assert cr == "cache"
            return Found(self.texts if "'name'" in repr(cond) else self.buttons)

    page = Doc(rect(0, 120, 1600, 900), buttons=[
        el("Einstellungen", rect(100, 700, 200, 740)), el("Alle akzeptieren", rect(220, 700, 360, 740)),
        el("Nur notwendige", rect(380, 700, 500, 740)), el("Accept", rect(0, 0, 50, 20), off=True),
        el("Akzeptieren", rect(10, 50, 90, 80))])
    banner_doc = Doc(rect(200, 600, 600, 800))
    root = types.SimpleNamespace(CurrentBoundingRectangle=rect(0, 0, 1600, 900),
                                 FindAllBuildCache=lambda scope, cond, cr: Found([banner_doc, page]))

    class Uia:
        def ElementFromHandle(self, h):
            return root

        def CreatePropertyCondition(self, pid, val):
            return ("prop", pid, val)

        def CreatePropertyConditionEx(self, pid, val, flags):
            return ("name", val)

        def CreateOrCondition(self, a, b):
            return ("or", a, b)

    class Cache(str):
        def AddProperty(self, pid):
            pass
    Uia.CreateCacheRequest = lambda self: Cache("cache")
    uac = types.ModuleType("comtypes.gen.UIAutomationClient")
    for i, k in enumerate(("TreeScope_Descendants", "UIA_ButtonControlTypeId", "UIA_ControlTypePropertyId",
                           "UIA_DocumentControlTypeId", "UIA_HyperlinkControlTypeId", "UIA_NamePropertyId",
                           "UIA_BoundingRectanglePropertyId", "UIA_IsOffscreenPropertyId",
                           "UIA_IsEnabledPropertyId")):
        setattr(uac, k, i + 1)
    gen = types.ModuleType("comtypes.gen")
    gen.UIAutomationClient = uac
    comtypes = types.ModuleType("comtypes")
    comtypes.gen = gen
    monkeypatch.setitem(sys.modules, "comtypes", comtypes)
    monkeypatch.setitem(sys.modules, "comtypes.gen", gen)
    monkeypatch.setitem(sys.modules, "comtypes.gen.UIAutomationClient", uac)
    monkeypatch.setattr(consent_win, "_automation", lambda: Uia())

    assert consent_win.find_consent_button(1) == ("accept", "Alle akzeptieren", (220, 700, 360, 740))
    assert consent_win.find_consent_button(1, True) == ("decline", "Nur notwendige", (380, 700, 500, 740))
    page.buttons, page.texts = [], [el("Alle akzeptieren", rect(220, 700, 360, 740))]
    assert consent_win.find_consent_button(1) == ("accept", "Alle akzeptieren", (220, 700, 360, 740))
    page.texts = []
    assert consent_win.find_consent_button(1) is None
