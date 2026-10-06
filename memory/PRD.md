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

## Umgesetzt v1.6.0 (2026-06)
- Tray „Nach Update suchen (installiert: vX)“: updater.py liest Version (awaketoggle/__init__.py) auf allen Branches von update_repo (GitHub API + raw), höchste > laufende → Ja/Nein-Dialog → Branch-ZIP nach %LOCALAPPDATA%\AwakeToggle\updates → Installieren.cmd in neuem Konsolenfenster; config update_repo
- 11 neue Themen (gaming, sport, musik, filme, fitness, mode, heimwerken, familie, nachrichten, wissenschaft, fernreisen) → 31 Themen; personas.py: 13 Persönlichkeiten mit Lieblingsthemen, Tempo, Lesedauer, Neugier, Lieblingsseiten, Ablehnquote; Rotation ohne Wiederholung unter den letzten 3
- Tab-Aufräumen: zufälliges Limit 3–6 je eigenem Fenster, Aktion alte_tabs_schliessen (3 Arten, nie 2× gleich hintereinander, Strg+W/Strg+F4, Strg+1), max. Limit+1; nur eigene Tabs; Restfenster nach Abbruch: Titel 6 s passiv nachführen, damit sie beim nächsten Lauf geschlossen werden
- Cookies: verzögerte Banner (bis 3 Abfragen), CacheRequest + größtes sichtbares Dokument, Fallback klickbare Texte per Name, meist akzeptieren / gelegentlich „Nur notwendige“/„Ablehnen“ (Persona-Quote, nur wenn Zustimmen-Button daneben), Nachkontrolle + 2. Klick, sonst Auffälligkeit
- 110 pytest-Tests grün (Windows-Teile simuliert); ZIP: /app/AwakeToggle_komplett.zip

## Umgesetzt v1.7.0 (2026-06)
- Lange Pausen: nach zufällig 60–120 min Dauerbetrieb (ohne Nutzeraktivität) macht eine Sitzung mittendrin 2–15 min Pause: Maus Richtung Minimieren, eigene Testfenster minimiert, danach wiederhergestellt; sonst nur warten; Nutzereingabe beendet sofort. Config browse_breaks, browse_break_minutes, browse_break_every_minutes; Tray-Schalter
- Sitzungen ohne Abstand: browse_chain_percent (Standard 20 %), nächste Sitzung nach 1,5–6 s, nur wenn Nutzer nicht aktiv; Tray-Untermenü 0/10/20/40 %
- Tab-Limit nur für eigene Tabs: Tableiste per UIA (tabs_win.py, RuntimeId + ausgewählt), eigene Tabs nur nach eigenen Öffnen-Aktionen; fremde Tabs zählen nicht, werden nie geschlossen/bedient, Fenster mit fremden Tabs bleibt offen; Fallback auf Plan-Zählung, wenn Tableiste unlesbar oder IDs instabil; --selftest zeigt „Tabs lesbar / IDs stabil“
- 148 pytest-Tests grün; ZIP: /app/AwakeToggle_komplett.zip

## Backlog
- P1 Echter Lauf mit Power Browser, Inkognito-Titel prüfen (--selftest)
- P1 --selftest auf echtem Windows: „Tabs lesbar … IDs stabil: ja“ prüfen
- P1 Update-Funktion auf echtem Windows testen (neuen Branch mit höherer Version anlegen)
- P2 Live-Status im Tooltip, CSV-Bericht, eigene Wortliste, Persönlichkeiten per Tray an/abwählen
