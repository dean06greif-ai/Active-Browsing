# AwakeToggle – Browser-Test (PRD)

## Problem statement
User's Windows tray tool (repo dean06greif-ai/Active-Browsing, Python/ctypes) should passively test the browser incl. search engine from outside: smart random sequences of Edge shortcuts – open/close/switch tabs & windows, search random numbers/words, wait, scroll, click.
User choices: Windows; risky shortcuts completely excluded (Alt+F4, Ctrl+Shift+W, Ctrl+Shift+Del, Ctrl+P, Ctrl+S, Ctrl+O, F12); queries = random numbers + word lists (topics, questions, typos).

## Architecture
- awaketoggle/queries.py – query generator (numbers, conversions, topics, questions, EN, typos, QWERTZ neighbors)
- awaketoggle/browse.py – state-aware scenario generator (37 actions, weights by tab/window/page state, moods, BLOCKED shortcuts)
- awaketoggle/browse_runner.py – executor: own windows only, focus check per step, user-input abort, popup closing, leftover cleanup, slow-load detection via window title
- awaketoggle/win32.py Desktop – ctypes window/process/keyboard(unicode, extended keys)/mouse layer
- core.Engine._browse, config keys browse_processes / browse_actions_max / browse_exclude, tray submenu "Browser-Test Länge"

## Implemented (2026-06)
- signal "browse" mode end-to-end, 43 pytest tests (FakeDesk simulation) pass on Linux
- README section "Browser-Test"
- NOT run on real Windows yet (only static review + CI selftest)

## Bug fix (2026-06)
- Browser-Test paused with "Browser nicht im Vordergrund (explorer.exe)": runner now brings the most recent browser window to front (restore minimized, SetForegroundWindow/Alt trick/AttachThreadInput); KNOWN_BROWSERS (Chrome, Edge, Brave, Vivaldi, Opera, …) always accepted; browse_processes = extra programs, default []
- 45 tests pass

## Backlog
- P1: real Windows test with Edge / Power Browser, tune toolbar offset & timings
- P1: CSV/HTML report of runs (load times per query)
- P2: custom word list file, smarter result-link clicking via UI Automation
