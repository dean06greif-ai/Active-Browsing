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

## Backlog
- P1 Echter Lauf mit Power Browser, Inkognito-Titel prüfen (--selftest)
- P2 Live-Status im Tooltip, CSV-Bericht, eigene Wortliste
