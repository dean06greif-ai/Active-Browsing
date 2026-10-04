import random

from awaketoggle import queries
from awaketoggle.browse import BrowserNames, ACTION_IDS, BLOCKED, MAX_TABS, VK, make_scenario
from awaketoggle.browse_runner import Runner
from awaketoggle.config import Config
from tests.test_core import make

NAMES = {v: k for k, v in VK.items()}
USER = 1


class FakeDesk:
    """Simulierter Desktop mit einem Chromium-ähnlichen Browser."""

    def __init__(self, user_proc="msedge.exe", popup_every=0, user_input_at_ms=None, new_private=False):
        self.ms = 1_000_000
        self.last = self.ms
        self.wins = {USER: {"proc": user_proc, "tabs": 3, "title": "Benutzer", "private": False}}
        self.z = [USER]
        self.next = 100
        self.sent = []
        self.clicks = 0
        self.popup_every = popup_every
        self.user_input_at = user_input_at_ms
        self.pos = (300, 300)
        self.activate_ok = True
        self.new_private = new_private

    # Zeit
    def sleep(self, s):
        self.ms += max(1, round(s * 1000))

    def clock(self):
        return self.ms / 1000

    def tick(self):
        return self.ms & 0xFFFFFFFF

    def last_input_tick(self):
        if self.user_input_at is not None and self.ms >= self.user_input_at:
            self.last = max(self.last, self.ms)  # Sie bewegen ab jetzt laufend die Maus
        return self.last & 0xFFFFFFFF

    def _input(self):
        self.last = self.ms

    # Fenster
    def foreground(self):
        return self.z[-1] if self.z else 0

    def root(self, h):
        return h

    def process_name(self, h):
        return self.wins[h]["proc"] if h in self.wins else ""

    def is_window(self, h):
        return h in self.wins

    def is_visible(self, h):
        return h in self.wins

    def is_app_window(self, h):
        return h in self.wins

    def title(self, h):
        if h not in self.wins:
            return ""
        w = self.wins[h]
        return f"{w['title']} - [InPrivate] - Microsoft Edge" if w.get("private") else w["title"]

    def window_rect(self, h):
        return 0, 0, 1600, 900

    def dpi(self, h):
        return 96

    def top_windows(self):
        return set(self.wins)

    def activate(self, h):
        if not self.activate_ok or h not in self.wins:
            return False
        self.z.remove(h)
        self.z.append(h)
        return True

    def find_browser(self, names, skip=lambda h: False):
        return next((h for h in reversed(self.z) if self.wins[h]["proc"] in names and not skip(h)), 0)

    def _open(self, private=False, title="Neuer Tab", proc="msedge.exe"):
        h = self.next
        self.next += 1
        self.wins[h] = {"proc": proc, "tabs": 1, "title": title, "private": private}
        self.z.append(h)
        return h

    def _close(self, h):
        del self.wins[h]
        self.z.remove(h)

    # Eingaben
    def cursor(self):
        return self.pos

    def move_to(self, x, y):
        self._input()
        self.pos = (x, y)

    def click(self, ctrl=False):
        self._input()
        h = self.foreground()
        if ctrl:
            self.wins[h]["tabs"] += 1
            return
        self.clicks += 1
        self.wins[h]["title"] = f"Seite {self.ms}"
        if self.popup_every and self.clicks % self.popup_every == 0:
            self._open(title="Popup", proc=self.wins[h]["proc"])

    def wheel(self, delta):
        self._input()

    def type_char(self, ch):
        self._input()
        self.sent.append((self.foreground(), ch))

    def send_combo(self, vks):
        self._input()
        name = "+".join(NAMES[v] for v in vks)
        h = self.foreground()
        self.sent.append((h, name))
        w = self.wins.get(h)
        if w is None:
            return
        if name == "ctrl+n":
            self._open(private=self.new_private or w.get("private", False), proc=w["proc"])
        elif name == "ctrl+shift+n":
            self._open(private=True)
        elif name in ("ctrl+t", "ctrl+shift+k", "ctrl+u"):
            w["tabs"] += 1
        elif name == "ctrl+w":
            w["tabs"] -= 1
            if w["tabs"] == 0:
                self._close(h)
        elif name in ("enter", "ctrl+enter"):
            w["title"] = f"Ergebnis {self.ms}"


def run(seed, cfg=None, **desk_kw):
    desk = FakeDesk(**desk_kw)
    cfg = cfg or Config(signal="browse")
    plan = make_scenario(cfg, random.Random(seed))
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(seed))
    return desk, runner, runner.run(plan, cfg.browse_processes)


def all_combos(plan):
    for _, steps in plan.steps:
        for s in steps:
            if s[0] in ("key", "nav", "new_window"):
                yield s[1]


def test_scenario_never_uses_blocked_shortcuts_and_is_balanced():
    for seed in range(300):
        plan = make_scenario(Config(signal="browse", browse_actions_max=40), random.Random(seed))
        combos = list(all_combos(plan))
        assert not set(combos) & BLOCKED
        assert not {"ctrl+shift+n", "ctrl+shift+t", "ctrl+shift+a"} & set(combos)
        assert plan.steps[0][1][0] == ("new_window", "ctrl+n")
        opened = sum(1 for _, st in plan.steps for s in st if s[0] == "new_window")
        closed = sum(1 for _, st in plan.steps for s in st if s[0] == "close_window")
        assert opened == closed
        assert plan.steps[-1][0] == "aufräumen"
        assert combos.count("f11") % 2 == 0 and combos.count("ctrl+shift+b") % 2 == 0
        assert combos.count("ctrl+m") % 2 == 0
        if "ctrl+add" in combos:
            assert "ctrl+0" in combos


def test_scenario_searches_with_numbers_and_respects_exclude():
    cfg = Config(signal="browse", browse_exclude=("klicken", "vollbild"))
    names, typed = set(), []
    for seed in range(200):
        plan = make_scenario(cfg, random.Random(seed))
        names |= {n for n, _ in plan.steps}
        typed += [s[1] for _, st in plan.steps for s in st if s[0] == "type"]
        assert all(s[1] != "ctrl+shift+n" for _, st in plan.steps for s in st if s[0] == "new_window")
    assert "suche" in names and not names & {"klicken", "inprivate_fenster", "tab_wiederherstellen", "vollbild"}
    assert sum(any(c.isdigit() for c in t) for t in typed) > 50
    assert len(names - {"aufräumen"}) > 24


def test_scenario_tab_model_stays_in_bounds():
    for seed in range(200):
        plan = make_scenario(Config(signal="browse", browse_actions_max=60), random.Random(seed))
        tabs = [1]
        for name, steps in plan.steps:
            for s in steps:
                if s[0] == "new_window":
                    tabs.append(1)
                elif s[0] == "close_window":
                    tabs.pop()
                elif (s[0] == "key" and s[1] in ("ctrl+t", "ctrl+shift+k")) or (s[0] == "click" and s[2]):
                    tabs[-1] += 1
                elif s[0] == "key" and s[1] == "ctrl+w" and name != "quelltext":
                    tabs[-1] -= 1
                    assert tabs[-1] >= 1
            assert all(t <= MAX_TABS for t in tabs[1:])


def test_runner_runs_and_cleans_up_without_touching_user_window():
    for seed in range(60):
        desk, _, res = run(seed)
        assert res.status == "done", (seed, res)
        assert set(desk.wins) == {USER} and desk.wins[USER]["tabs"] == 3
        user_keys = [k for h, k in desk.sent if h == USER]
        assert user_keys == ["ctrl+n"], (seed, user_keys)
        assert desk.pos == (300, 300)


def test_runner_skips_when_no_browser_window_exists():
    desk, _, res = run(1, user_proc="notepad.exe")
    assert res.status == "skipped" and "kein Browserfenster" in res.text and "notepad.exe" in res.text
    assert desk.sent == []


def test_runner_brings_browser_to_front_when_tray_or_desktop_is_active():
    desk = FakeDesk(user_proc="chrome.exe")
    desk.wins[2] = {"proc": "explorer.exe", "tabs": 1, "title": "Taskleiste", "private": False}
    desk.z.append(2)
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(3))
    res = runner.run(make_scenario(Config(signal="browse"), random.Random(3)), ())
    assert res.status == "done", res
    assert all(h != 2 for h, _ in desk.sent)
    assert [k for h, k in desk.sent if h == USER] == ["ctrl+n"]
    assert set(desk.wins) == {USER, 2}


def test_browser_names_include_power_browser():
    from awaketoggle.browse import BrowserNames
    names = BrowserNames(("mybrowserx.exe", "PB.exe"))
    for n in ("powerbrowser.exe", "Power Browser.exe", "PowerBrowserApp.exe", "chrome.exe", "msedge.exe", "pb.exe"):
        assert n in names, n
    for n in ("explorer.exe", "notepad.exe", "powershell.exe", "code.exe", "discord.exe", "", None):
        assert n not in names, n


def test_runner_finds_power_browser_behind_taskbar():
    desk = FakeDesk(user_proc="powerbrowser.exe")
    desk.wins[2] = {"proc": "explorer.exe", "tabs": 1, "title": "Taskleiste", "private": False}
    desk.z.append(2)
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(4))
    res = runner.run(make_scenario(Config(signal="browse"), random.Random(4)), ())
    assert res.status == "done", res
    assert set(desk.wins) == {USER, 2} and all(h != 2 for h, _ in desk.sent)


def test_runner_accepts_custom_browser_and_skips_if_activation_fails():
    desk = FakeDesk(user_proc="pb.exe")
    desk.wins[2] = {"proc": "explorer.exe", "tabs": 1, "title": "Desktop", "private": False}
    desk.z.append(2)
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(1))
    plan = make_scenario(Config(signal="browse"), random.Random(1))
    assert runner.run(plan, ()).status == "skipped"
    desk.activate_ok = False
    res = runner.run(plan, ("pb.exe",))
    assert res.status == "skipped" and "nicht nach vorne" in res.text and desk.sent == []
    desk.activate_ok = True
    assert runner.run(plan, ("pb.exe",)).status == "done"


def test_runner_aborts_on_user_input_and_cleans_up_next_time():
    desk, runner, res = run(5, user_input_at_ms=1_000_000 + 4_000)
    assert res.status == "aborted" and res.text == "Sie sind aktiv"
    count = len(desk.sent)
    desk.sleep(3)
    assert len(desk.sent) == count
    leftover = [h for h in desk.wins if h != USER]
    assert [h for h, _ in runner.leftover] == leftover and leftover
    desk.user_input_at = None
    desk.activate(USER)
    res = runner.run(make_scenario(Config(signal="browse"), random.Random(9)), ("msedge.exe",))
    assert res.status == "done" and set(desk.wins) == {USER}


def test_runner_closes_popups_opened_by_clicks():
    seen = 0
    for seed in range(80):
        desk, _, res = run(seed, popup_every=1)
        assert res.status == "done", (seed, res)
        assert set(desk.wins) == {USER}
        if desk.clicks:
            seen += 1
            assert any("Popup" in p for p in res.problems)
    assert seen > 10


def test_runner_stops_when_focus_moves_to_foreign_window():
    desk = FakeDesk()
    desk.activate_ok = False
    plan = make_scenario(Config(signal="browse"), random.Random(2))
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(2))
    orig = desk.send_combo

    def steal(vks):
        orig(vks)
        if len(desk.sent) == 6:
            desk.wins[50] = {"proc": "explorer.exe", "tabs": 1, "title": "Fremd", "private": False}
            desk.z.append(50)
    desk.send_combo = steal
    res = runner.run(plan, ("msedge.exe",))
    desk.wins[50]["tabs"] = 1
    assert res.status == "aborted"
    assert all(h != 50 for h, _ in desk.sent)


def test_queries_variety():
    rng = random.Random(4)
    qs = [queries.make_query(rng) for _ in range(500)]
    assert all(q.strip() for q in qs)
    assert len(set(qs)) > 250
    assert sum(any(c.isdigit() for c in q) for q in qs) > 60
    assert queries.typo("wetter berlin", random.Random(1)) != "wetter berlin"


def test_engine_browse_mode():
    from awaketoggle.browse_runner import Result
    api, _, eng = make(Config(signal="browse"))
    calls = []

    def browse(plan, cfg, cancel):
        calls.append(plan)
        assert not cancel()
        api.last = api.now
        return Result("done", "12 Aktionen in 90 s")
    api.browse = browse
    eng.set_active(True)
    api.advance(60_000)
    assert eng.step() == 60.0
    assert len(calls) == 1 and calls[0].kind == "browse"
    assert "Browser-Test" in eng.status.text and eng.status.state == "on"
    api.advance(30_000)
    eng.step()
    assert len(calls) == 1
    api.browse = lambda plan, cfg, cancel: Result("skipped", "Browser nicht im Vordergrund (x.exe)")
    api.advance(60_000)
    eng.step()
    assert eng.status.state == "paused" and "x.exe" in eng.status.text


def test_config_browse_keys(tmp_path):
    import json
    from awaketoggle.config import load
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"signal": "browse", "browse_processes": ["MSEdge.exe ", "chrome.exe"],
                             "browse_actions_max": 40, "browse_exclude": ["klicken"]}), "utf-8")
    cfg, warnings = load(p)
    assert warnings == [] and cfg.signal == "browse"
    assert cfg.browse_processes == ("msedge.exe", "chrome.exe") and cfg.browse_exclude == ("klicken",)
    p.write_text(json.dumps({"browse_processes": [""], "browse_actions_max": 500, "browse_exclude": ["xyz"]}), "utf-8")
    cfg, warnings = load(p)
    assert len(warnings) == 3 and cfg == Config()
    assert set(ACTION_IDS) >= {"suche", "neuer_tab", "tab_schliessen", "klicken", "lesen_scrollen"}


def test_power_exe_is_browser():
    from awaketoggle.browse import BrowserNames
    names = BrowserNames()
    assert "power.exe" in names and "Power.exe" in names
    for n in ("powershell.exe", "powertoys.exe", "explorer.exe"):
        assert n not in names


def test_runner_uses_unknown_front_window_process():
    desk = FakeDesk(user_proc="mycustom.exe")
    desk.find_browser = lambda names, skip=None: USER
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock)
    assert r._bring_browser_to_front(BrowserNames()) == USER


def test_badge_parse_and_compare():
    from awaketoggle.badge import compare, parse_number
    assert parse_number("698") == 698
    assert parse_number("Rewards: 1.2k") == 1200
    assert parse_number("Punkte 1.234") == 1234
    assert parse_number("Meine Erweiterung") is None
    assert compare(698, 712) == ("Zähler 698 → 712", None)
    assert compare(698, 698)[1].startswith("Zähler nicht gestiegen")
    assert compare(None, None) == ("", None)


def test_runner_reads_badge_before_and_after():
    desk = FakeDesk()
    values = iter([698, 698])
    r = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(1))
    plan = make_scenario(Config(browse_actions_max=3), random.Random(1))
    res = r.run(plan, (), badge=lambda h: next(values))
    assert res.status == "done"
    assert "Zähler 698 → 698" in res.text
    assert any("nicht gestiegen" in p for p in res.problems)


def test_badge_win_generates_comtypes_module_before_import(monkeypatch):
    import sys
    import types
    from awaketoggle import badge_win

    calls = []
    rect = types.SimpleNamespace(left=0, top=0, right=40, bottom=40)

    class El:
        CurrentBoundingRectangle = rect
        CurrentName, CurrentHelpText, CurrentClassName = "Rewards 698", "", "ToolbarActionView"

        def FindAll(self, scope, cond):
            return types.SimpleNamespace(Length=0)

    class Found:
        Length = 1

        def GetElement(self, i):
            return El()

    class Uia:
        def ElementFromHandle(self, h):
            return types.SimpleNamespace(CurrentBoundingRectangle=rect, FindAll=lambda scope, cond: Found())

        def CreatePropertyCondition(self, *a):
            return a

        def CreateOrCondition(self, *a):
            return a

        def CreateTrueCondition(self):
            return True

    def get_module(name):
        calls.append(name)
        gen = types.ModuleType("comtypes.gen")
        uac = types.ModuleType("comtypes.gen.UIAutomationClient")
        for k in ("CUIAutomation", "IUIAutomation", "TreeScope_Descendants", "UIA_ButtonControlTypeId",
                  "UIA_ControlTypePropertyId", "UIA_MenuItemControlTypeId"):
            setattr(uac, k, 1)
        gen.UIAutomationClient = uac
        sys.modules["comtypes.gen"], sys.modules["comtypes.gen.UIAutomationClient"] = gen, uac

    comtypes = types.ModuleType("comtypes")
    comtypes.COINIT_MULTITHREADED = 0
    comtypes.CoInitializeEx = lambda flags: None
    client = types.ModuleType("comtypes.client")
    client.GetModule = get_module
    client.CreateObject = lambda cls, interface=None: Uia()
    comtypes.client = client
    for k in ("comtypes.gen", "comtypes.gen.UIAutomationClient"):
        monkeypatch.delitem(sys.modules, k, raising=False)
    monkeypatch.setitem(sys.modules, "comtypes", comtypes)
    monkeypatch.setitem(sys.modules, "comtypes.client", client)
    monkeypatch.setattr(badge_win, "_uia", None)

    assert badge_win.read_badge(1) == 698
    assert calls == ["UIAutomationCore.dll"]
    for k in ("comtypes.gen", "comtypes.gen.UIAutomationClient"):
        sys.modules.pop(k, None)


def test_badge_candidates_prefer_power_points_button():
    from awaketoggle.badge_win import _candidates
    buttons = [("Erweiterungen", "", "ExtensionsToolbarButton", (0, 0, 1, 1), None),
               ("Power Coins", "", "PowerGuardButtonView", (0, 0, 1, 1), None),
               ("Neu laden", "", "ReloadButton", (0, 0, 1, 1), None),
               ("Power Coins", "", "PowerPointsActionView", (0, 0, 1, 1), None)]
    got = [b[2] for b in _candidates(buttons)]
    assert got[0] == "PowerPointsActionView"
    assert "ExtensionsToolbarButton" not in got and "ReloadButton" not in got


def test_private_titles_are_detected():
    from awaketoggle.browse import is_private
    for t in ("Neuer Tab - [InPrivate] - Microsoft Edge", "Neuer Inkognito-Tab - Google Chrome (Inkognito)",
              "New Tab - Google Chrome (Incognito)", "Mozilla Firefox – Privater Modus"):
        assert is_private(t), t
    for t in ("Neuer Tab - Microsoft Edge", "wetter 4711 - Suche", "", None):
        assert not is_private(t), t
    assert is_private("Startseite - Power Browser (Geheim)", ("(geheim)",))


def test_runner_never_uses_private_user_window_and_takes_normal_one():
    desk = FakeDesk()
    desk.wins[2] = {"proc": "msedge.exe", "tabs": 2, "title": "Privat", "private": True}
    desk.z.append(2)
    for seed in range(20):
        runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(seed))
        res = runner.run(make_scenario(Config(signal="browse"), random.Random(seed)), ())
        assert res.status == "done", (seed, res)
        assert all(h != 2 for h, _ in desk.sent)
        assert desk.wins[2]["tabs"] == 2 and desk.wins[USER]["tabs"] == 3
        assert set(desk.wins) == {USER, 2}
        desk.activate(2)


def test_runner_skips_when_only_private_windows_exist():
    desk = FakeDesk()
    desk.wins[USER]["private"] = True
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(1))
    res = runner.run(make_scenario(Config(signal="browse"), random.Random(1)), ())
    assert res.status == "skipped" and "Inkognito" in res.text
    assert desk.sent == []


def test_runner_closes_own_window_immediately_if_it_is_private():
    desk = FakeDesk(new_private=True)
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(2))
    res = runner.run(make_scenario(Config(signal="browse"), random.Random(2)), ())
    assert res.status == "aborted" and "Inkognito" in res.text
    assert set(desk.wins) == {USER} and desk.wins[USER]["tabs"] == 3
    assert [k for h, k in desk.sent if h == USER] == ["ctrl+n"]
    assert all(k in ("ctrl+n", "ctrl+w") for _, k in desk.sent)


def test_runner_custom_private_words():
    desk = FakeDesk(user_proc="powerbrowser.exe")
    desk.wins[USER]["title"] = "Startseite - Power Browser (Geheim)"
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(1))
    res = runner.run(make_scenario(Config(signal="browse"), random.Random(1)), (), private_words=("(geheim)",))
    assert res.status == "skipped" and desk.sent == []


def test_runner_never_touches_foreign_window_that_appears_without_click():
    cfg = Config(signal="browse", browse_exclude=("klicken", "ergebnis_oeffnen", "im_tab_oeffnen"))
    for seed in range(30):
        desk = FakeDesk()
        runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(seed))
        orig, n = desk.send_combo, [0]

        def spawn(vks):
            orig(vks)
            n[0] += 1
            if n[0] >= 4 and not hasattr(desk, "foreign") and NAMES[vks[-1]] != "n":
                desk._open(title="Fremdes Fenster (z. B. Link aus Mail)")
                desk.foreign = desk.next - 1
        desk.send_combo = spawn
        res = runner.run(make_scenario(cfg, random.Random(seed)), ())
        foreign = getattr(desk, "foreign", None)
        if foreign is None:
            continue
        assert foreign in desk.wins and desk.wins[foreign]["tabs"] == 1, (seed, res)
        assert all(h != foreign for h, _ in desk.sent), (seed, res)
        assert res.status == "done", (seed, res)


def test_leftover_window_used_by_user_is_not_closed():
    desk, runner, res = run(5, user_input_at_ms=1_000_000 + 4_000)
    assert res.status == "aborted" and runner.leftover
    h = runner.leftover[0][0]
    desk.wins[h]["title"] = "Vom Benutzer weiterbenutzt"
    desk.user_input_at = None
    desk.activate(USER)
    res = runner.run(make_scenario(Config(signal="browse"), random.Random(9)), ())
    assert res.status == "done" and h in desk.wins


def test_config_drops_removed_action_ids_and_reads_private_words(tmp_path):
    import json
    from awaketoggle.config import load
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"browse_exclude": ["inprivate_fenster", "tab_wiederherstellen", "zoom"],
                             "browse_private_words": [" (Geheim) "]}), "utf-8")
    cfg, warnings = load(p)
    assert warnings == [] and cfg.browse_exclude == ("zoom",) and cfg.browse_private_words == ("(geheim)",)


def test_sessions_look_human():
    from awaketoggle.browse import RARE, MAX_RARE
    from awaketoggle.queries import Interest
    tot = rare = 0
    for seed in range(300):
        plan = make_scenario(Config(signal="browse"), random.Random(seed))
        names = [n for n, _ in plan.steps[1:-1]]
        assert sum(n in RARE for n in names) <= MAX_RARE
        if "suche_verfeinern" in names:
            assert names.index("suche_verfeinern") > min(names.index(n) for n in ("suche", "neuer_tab") if n in names)
        tot += len(names)
        rare += sum(n in RARE for n in names)
    assert rare / tot < 0.1
    it = Interest(random.Random(3), "wetter")
    first, refined = it.first(), it.next()
    assert "wetter" in first and refined != first


def test_typing_rhythm_is_irregular():
    from awaketoggle.browse import Builder
    b = Builder(random.Random(1), "normal")
    b.type("wetter berlin morgen")
    delays = b.steps[0][2]
    assert max(delays) > 2 * min(delays)
    assert len(set(delays)) > len(delays) * 0.8
