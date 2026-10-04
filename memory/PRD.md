# AwakeToggle – Browser-Test (Active-Browsing)

## Problem
Windows-Tray-Tool (Python) testet den eigenen Browser (Power Browser) per Langzeit-Browsing. Basis: Branch conflict_031026_1038 + gefixte Dateien aus conflict_041026_1037 (awaketoggle_fix/). Fehler: Tester ging in Inkognito-Tabs und bediente fremde Tabs/Fenster.
User-Wunsch: immer komplette Dateien liefern (keine Patches); ZIP + Save to GitHub.

## Umgesetzt (2026-06)
- Branches zusammengeführt nach /app (awaketoggle/, tests/, tools/, .github, main.py, requirements*, README.md), v1.2.0
- Nie Inkognito: Strg+Shift+N gesperrt, Aktion inprivate_fenster entfernt, private Ausgangsfenster werden übersprungen (Titelerkennung is_private + config browse_private_words), eigenes Fenster wird sofort geschlossen falls doch privat
- Nur eigene Tabs/Fenster: Strg+Shift+T + Strg+Shift+A gesperrt, tab_wiederherstellen entfernt; keine Eingaben ohne eigenes Fenster; fremde neue Fenster nie geschlossen (Popups nur ≤8 s nach eigenem Klick); neues Fenster muss eindeutig sein; Reste nur schließen wenn Titel unverändert
- Selftest listet Browserfenster mit normal/Inkognito
- 67 pytest-Tests grün (FakeDesk, Win32 simuliert); ZIP: /app/AwakeToggle_komplett.zip

## Umgesetzt v1.3.0 (2026-06)
- Installieren.cmd / Deinstallieren.cmd (tools/installieren.ps1): pip, exe-Bau (noconsole), Kopie nach %LOCALAPPDATA%\Programs\AwakeToggle, Desktop+Startmenü-Verknüpfung, Autostart-Link aktualisiert; Fallback pythonw
- Tray: "Verknüpfung auf Desktop + Startmenü anlegen", "Weg-Modus" Schalter
- Weg-Modus (away.py + power_win.py): bei Arbeit Helligkeit 0 % (WMI + DDC/CI), Energiesparmodus (ESBATTTHRESHOLD 100) + Overlay beste Effizienz; bei Rückkehr (Watcher 0,3 s) 50 % + vorheriger Zustand; Recovery via away_state.json
- Config: away_power, away_brightness, back_brightness, away_energy_saver; 79 Tests grün

## Umgesetzt v1.4.0 (2026-06) – menschliches Surfen
- queries.Interest: ~20 Themen mit Start/Verfeinerung/verwandten Fragen (roter Faden), realistische Zahlen, 12 % Tippfehler
- browse.py: Person (Lieblingstasten, Neugier, Lesedauer), Seitenzustand leer/ergebnisse/seite, ergebnis_oeffnen, im_tab_oeffnen (Strg+Klick) + Lesen im Tab, suche_verfeinern; log-normal Pausen; Tipprhythmus + spät bemerkte Vertipper; seltene Funktionen max 2/Durchlauf, nie zuerst
- Runner: Maus-Bogen mit Überschießen, nudge beim Lesen, Strg+Klick; 88 Tests grün

## Backlog
- P1 Echter Lauf mit Power Browser, Inkognito-Titel prüfen (--selftest)
- P2 Live-Status im Tooltip, CSV-Bericht, eigene Wortliste
