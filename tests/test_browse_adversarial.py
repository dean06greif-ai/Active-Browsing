"""Adversarial tests: ensure runner never sends input to windows it did not open.

Policies under test (per review request):
- USER window may ONLY ever receive 'ctrl+n'.
- No clicks/keystrokes may reach a foreign window (including same-process ones
  that pop up during polling after a ctrl+n, or new browser windows that appear
  unprompted).
- Leftover foreign windows that look like a user-opened browser must not be
  closed by cleanup.
"""
import random

from awaketoggle.browse import make_scenario
from awaketoggle.browse_runner import Runner
from awaketoggle.config import Config

from tests.test_browse import FakeDesk, NAMES, USER


def _run(desk, seed, cfg=None):
    cfg = cfg or Config(signal="browse")
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(seed))
    plan = make_scenario(cfg, random.Random(seed))
    res = runner.run(plan, cfg.browse_processes)
    return runner, res


def test_user_window_only_ever_receives_ctrl_n_across_many_seeds():
    """Across many permutations/pop-ups, USER window must never receive anything but ctrl+n."""
    for seed in range(120):
        desk = FakeDesk()
        _, res = _run(desk, seed)
        user_keys = [k for h, k in desk.sent if h == USER]
        assert user_keys == ["ctrl+n"], (seed, user_keys, res.status)


def test_foreign_same_proc_window_appearing_after_ctrl_n_is_not_captured_as_own():
    """If a foreign same-process browser window pops up right during the new-window
    polling (not opened by us), the runner must NOT send input to it. Ideally it
    is detected as foreign; at minimum nothing is sent to the user's base window
    other than ctrl+n and the foreign window's tabs stay intact.
    """
    for seed in range(40):
        desk = FakeDesk()
        orig = desk.send_combo
        state = {"spawned": False}

        def wrap(vks, _orig=orig, _desk=desk, _state=state):
            _orig(vks)
            # When runner sends its very first ctrl+n to the base window, also
            # spawn a foreign same-proc window after our own window opens.
            if not _state["spawned"] and NAMES[vks[-1]] == "n" and len(vks) == 2:
                # ctrl+n -> fakedesk already opened one; now spawn a foreign one on top
                h = _desk._open(title="Fremder Browser (ext. geoeffnet)",
                                proc=_desk.wins[USER]["proc"])
                _state["foreign"] = h
                _state["spawned"] = True

        desk.send_combo = wrap
        _, res = _run(desk, seed)
        foreign = state.get("foreign")
        if foreign is None:
            continue
        # Foreign window must never receive any input, period.
        assert all(h != foreign for h, _ in desk.sent), (
            seed, res.status, "runner sent input to foreign same-proc window")


def test_leftover_foreign_proc_window_is_never_closed():
    """A leftover handle whose process is no longer a known browser proc
    (e.g. user replaced the window) must not be touched by cleanup."""
    desk, runner, res = None, None, None
    from tests.test_browse import run as _run_helper
    desk, runner, res = _run_helper(5, user_input_at_ms=1_000_000 + 4_000)
    assert res.status == "aborted" and runner.leftover
    h = runner.leftover[0][0]
    # Simulate user "took over" that window: now shows a different process
    desk.wins[h]["proc"] = "notepad.exe"
    desk.user_input_at = None
    desk.activate(USER)
    before_sent = len(desk.sent)
    res2 = runner.run(make_scenario(Config(signal="browse"), random.Random(9)),
                      ("msedge.exe",))
    # The foreign-proc leftover must still be there
    assert h in desk.wins
    # And it must never have received any input in the follow-up run
    assert all(hh != h for hh, _ in desk.sent[before_sent:])


def test_no_input_sent_when_only_private_windows():
    """When only private windows exist, runner must send nothing anywhere."""
    desk = FakeDesk()
    desk.wins[USER]["private"] = True
    runner = Runner(desk, sleep=desk.sleep, clock=desk.clock, rng=random.Random(0))
    res = runner.run(make_scenario(Config(signal="browse"), random.Random(0)), ())
    assert res.status == "skipped"
    assert desk.sent == []


def test_runner_never_sends_blocked_combos_at_runtime():
    """Even under stress and popups, the sent list must never contain any BLOCKED combo."""
    from awaketoggle.browse import BLOCKED
    for seed in range(60):
        desk = FakeDesk(popup_every=2)
        _, _ = _run(desk, seed)
        for _, k in desk.sent:
            # Only key combos; typed chars won't be in BLOCKED anyway
            assert k not in BLOCKED, (seed, k)
