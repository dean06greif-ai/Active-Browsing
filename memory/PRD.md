# AwakeToggle – PRD

## Problem
Kleines Python-Tray-Tool für Windows 10/11: hält Windows wach (SetThreadExecutionState) und sendet in festen Abständen
eine offene Eingabe (Maus 1 px hin/zurück oder F15) per SendInput, damit die Leerlauferkennung des eigenen Power Browser
nicht anschlägt. Pausiert bei eigener Eingabe (GetLastInputInfo) und bei gesperrtem Bildschirm. Verteilung als .exe über GitHub Releases.

## Nutzerentscheidungen
- Autostart als Tray-Menüpunkt (Verknüpfung im Autostart-Ordner, keine Registry), standardmäßig aus
- Deutsch für Menü und Protokoll
- Phasen 1–3 komplett
- Abstand, Signalart, Timer auch im Tray-Menü umschaltbar

## Architektur (/app)
- awaketoggle/core.py – Engine (Worker-Thread, Event.wait), decide()-Logik, Timer, Status
- awaketoggle/win32.py – ctypes: SendInput, GetLastInputInfo, SetThreadExecutionState, Mutex, Sperrerkennung, Selbsttest
- awaketoggle/session.py – verstecktes Fenster: WM_ENDSESSION, WTS-Sperrereignisse, Energiesparereignisse
- awaketoggle/tray.py, tray_labels.py, icons.py – pystray-Menü, Symbole grau/grün/gelb
- awaketoggle/config.py, logsetup.py, autostart.py, app.py
- tools/build.ps1, tools/make_icon.py, tools/eingabetest.html; .github/workflows/build.yml
- tests/ – 24 pytest-Tests (Logik, Konfiguration, Symbole)

## Umgesetzt (2026-06)
- Phase 1–3: Kern, Tray, config.json, Timer, Protokoll (2×512 KB), Sperrerkennung, Wirkungsprüfung des Signals,
  Einzelinstanz, sauberes Beenden, Autostart, GitHub-Actions-Build + Release bei Tag v*, README (DE)
- Tests: 24/24 grün (Linux). Win32-Code nur statisch geprüft; Prüfung auf Windows per --selftest im CI.

## Iteration 2 (2026-06)
- Zufallsmodus `signal: random` mit Varianten Mauspfad (zurück zum Start), Scrollen (hin/zurück), Tippen (nur F13–F24)
- `jitter_percent` 0–50: Abstand zufällig nur kürzer; Tray-Menü: Varianten-Häkchen, „Abstand variieren“
- Eingabetest-Seite protokolliert jetzt auch Scrollen; 32/32 Tests grün

## Backlog
- P0: Phase 4 auf echtem Windows mit Power Browser (Maus vs. F15, RAM, Ruhezustand, Sperre, RDP)
- P1: Sofortiges Signal vor dem Sperren / Hotkey zum Umschalten
- P2: Status-Panel (React + FastAPI, nur localhost), Code-Signatur gegen SmartScreen
