# AwakeToggle

Kleines Tray-Tool für Windows 10/11: hält den Rechner wach und sendet in festen Abständen eine einfache,
offene Eingabe (Maus 1 Pixel hin und zurück oder Taste F15), damit die Leerlauferkennung des eigenen
Power Browser nicht anschlägt. Ein- und Ausschalten mit einem Klick auf das Symbol im Infobereich.

Standard ist ein festes, gleichbleibendes Signal. Optional gibt es einen Modus **Zufällig** mit wechselnden,
harmlosen Varianten und einen Modus **Browser-Test**, der den Browser samt Suchmaschine passiv von außen testet:
Fenster und Tabs öffnen, zufällige Suchanfragen, lesen, scrollen, klicken, Tabs wechseln/schließen usw. (siehe unten).

| Symbol | Bedeutung |
|---|---|
| grau | aus |
| grün | an (wach halten + Signal) |
| gelb | an, aber pausiert (Bildschirm gesperrt oder Signal ohne Wirkung) |

## Installation (empfohlen: aus dem Quelltext, ein Doppelklick)

Voraussetzung: Python 3.12 (bei der Installation „Add python.exe to PATH“ anhaken).

1. Repo herunterladen/entpacken.
2. **`Installieren.cmd` doppelklicken.** Das Skript
   - installiert die Python-Pakete,
   - baut `AwakeToggle.exe` (ohne Konsolenfenster),
   - beendet ein evtl. laufendes AwakeToggle und kopiert die exe nach `%LOCALAPPDATA%\Programs\AwakeToggle\`,
   - legt die Verknüpfung **„AwakeToggle“ auf dem Desktop und im Startmenü** an (eine vorhandene Autostart-Verknüpfung
     wird mit aktualisiert) und startet das Programm.
3. Ab jetzt einfach per Desktop-Symbol oder Startmenü starten – **VS Code und Terminal werden nicht mehr gebraucht.**
   Das Programm läuft unsichtbar im Infobereich (Pfeil ^ unten rechts). Beenden über Rechtsklick → *Beenden*.

Nach Code-Änderungen einfach erneut `Installieren.cmd` ausführen. Sollte der exe-Bau scheitern, legt das Skript die
Verknüpfungen stattdessen auf `pythonw.exe main.py` an (läuft ebenfalls ohne Konsolenfenster).
Entfernen: **`Deinstallieren.cmd`** (Einstellungen in `%LOCALAPPDATA%\AwakeToggle` bleiben erhalten).

### Alternative: fertige exe

1. Unter **Releases** die neueste `AwakeToggle.exe` herunterladen (optional mit `AwakeToggle.exe.sha256` prüfen:
   `Get-FileHash .\AwakeToggle.exe -Algorithm SHA256`).
2. In einen festen Ordner legen, z. B. `%LOCALAPPDATA%\Programs\AwakeToggle\`, und starten.
   Keine Installation, keine Administratorrechte.

### SmartScreen-Hinweis

Die `.exe` ist nicht signiert. Beim ersten Start meldet Windows Defender SmartScreen
„Der Computer wurde durch Windows geschützt“. Auf **Weitere Informationen** und dann **Trotzdem ausführen**
klicken. Die Meldung erscheint pro Datei nur einmal. Wer der Datei nicht traut, baut sie selbst (siehe unten).

## Bedienung

- **Linksklick** auf das Symbol: ein/aus.
- **Rechtsklick** öffnet das Menü:
  - *Aktiv* – ein/aus, darunter der aktuelle Status
  - *Signal* – Maus (1 Pixel hin und zurück), Taste F15, *Zufällig* oder *Browser-Test*; darunter die Zufallsvarianten zum An-/Abhaken
  - *Browser-Test Länge* – kurz / mittel / lang (bis 10 / 20 / 40 Aktionen je Durchlauf)
  - *Abstand variieren* – nein, oder zufällig bis zu 10 / 25 / 50 % kürzer
  - *Jetzt testen* – startet sofort einen Durchlauf (schaltet bei Bedarf ein), ohne auf den Abstand zu warten
  - *Abstand* – 5 s, 10 s, 15 s, 30 s, 60 s, 2 min, 5 min oder *Eigener Wert eingeben …* (1–3600 s)
  - *Weg-Modus* – solange das Programm für Sie arbeitet: Helligkeit 0 % + Stromsparmodus an; sobald Sie wieder da sind:
    Helligkeit 50 % + Stromsparmodus aus (siehe unten)
  - *Automatisch abschalten* – nie, nach 1, 4 oder 8 Stunden (Timer startet beim Einschalten)
  - *Beim Programmstart aktivieren*
  - *Mit Windows starten* – legt eine Verknüpfung im Autostart-Ordner an (`shell:startup`), keine Registry
  - *Verknüpfung auf Desktop + Startmenü anlegen* – falls Sie sie gelöscht haben
  - *Konfiguration öffnen / neu laden*, *Protokoll öffnen*, *Beenden*
- Der Tooltip zeigt Status, letztes Signal und ggf. die Abschaltzeit.

## Konfiguration

Datei: `%LOCALAPPDATA%\AwakeToggle\config.json` (wird beim ersten Start angelegt; Menüänderungen werden sofort gespeichert).

```json
{
  "interval_seconds": 60,
  "signal": "mouse",
  "timer_hours": 0,
  "start_active": false,
  "verbose_log": false,
  "random_variants": ["mouse", "scroll", "keys"],
  "jitter_percent": 0,
  "browse_processes": [],
  "browse_actions_max": 20,
  "browse_exclude": [],
  "browse_private_words": [],
  "away_power": true,
  "away_brightness": 0,
  "back_brightness": 50,
  "away_energy_saver": true
}
```

| Schlüssel | Werte | Bedeutung |
|---|---|---|
| `interval_seconds` | 1–3600 | Abstand zwischen zwei Signalen |
| `signal` | `mouse` / `f15` / `random` / `browse` | Art des Signals |
| `timer_hours` | 0–24 (0 = unbegrenzt) | automatisch abschalten nach … Stunden |
| `start_active` | `true` / `false` | beim Programmstart sofort einschalten |
| `verbose_log` | `true` / `false` | jedes gesendete Signal protokollieren (für Tests) |
| `random_variants` | Liste aus `mouse`, `scroll`, `keys` | Varianten für `signal: random` (mind. eine) |
| `jitter_percent` | 0–50 | Abstand zufällig um bis zu so viel Prozent **kürzer** (nie länger) |
| `browse_processes` | Liste von Programmnamen | **zusätzliche** Browser; immer erkannt: Power Browser, Edge, Chrome, Brave, Vivaldi, Opera, Chromium, Thorium, Arc, Yandex, `power.exe` und jedes Programm mit „browser“ oder „power…“ im Namen (außer PowerShell/PowerToys). Wird keiner gefunden, wird das oberste normale Programmfenster genommen (Explorer/Taskleiste/Startmenü und unsichtbare Windows-Fenster werden ignoriert) |
| `browse_actions_max` | 3–100 | höchstens so viele Aktionen pro Browser-Test-Durchlauf (mindestens ein Drittel davon) |
| `browse_exclude` | Liste von Aktions-IDs | diese Aktionen nie ausführen (IDs siehe Tabelle unten) |
| `badge_read` | `true` / `false` | Zähler (Badge) einer Erweiterung vor und nach jedem Browser-Test lesen |
| `badge_extension` | Text | Teil des Erweiterungsnamens (Tooltip), z. B. `"Rewards"`; leer = erste Erweiterung mit Zahl |
| `browse_private_words` | Liste von Titelwörtern | **zusätzliche** Wörter, an denen ein Inkognito-Fenster im Fenstertitel erkannt wird (immer erkannt: InPrivate, Incognito, Inkognito, Privater Modus, Private Browsing …). Nötig nur, wenn Ihr Browser ein eigenes Wort nutzt – `--selftest` zeigt alle Browserfenster mit Titel und „normal“/„Inkognito“ |
| `away_power` | `true` / `false` | Weg-Modus an/aus |
| `away_brightness` | 0–100 | Helligkeit in %, solange das Programm arbeitet |
| `back_brightness` | 0–100 | Helligkeit in %, sobald Sie wieder da sind |
| `away_energy_saver` | `true` / `false` | im Weg-Modus auch den Stromsparmodus einschalten |

Nach Änderungen von Hand: Menü → *Konfiguration neu laden*. Ungültige Werte werden durch Standardwerte ersetzt und
im Protokoll gemeldet; eine unlesbare Datei wird als `config.invalid.json` gesichert.

Protokoll: `%LOCALAPPDATA%\AwakeToggle\awaketoggle.log` (+ eine Sicherung `.log.1`, zusammen höchstens 1 MB).

## Zufallsmodus

Bei `signal: random` wählt jedes Signal zufällig eine der aktivierten Varianten:

| Variante | Ablauf | Nettowirkung |
|---|---|---|
| Mausbewegung | 3–7 kleine Schritte (je bis 4 px, 8–40 ms Pause), dann derselbe Weg zurück; Position wird zum Schluss geprüft | Zeiger steht wieder am Ausgangspunkt (max. ca. 28 px Ausschlag) |
| Scrollen | 1–3 kleine Radschritte (15–60 von 120 je Raste) in eine Richtung, kurze Pause, dieselben zurück | Seite steht wieder an derselben Stelle |
| Tippen | 1–3 Tastendrücke aus **F13–F24** mit zufälliger Haltedauer und Pause | kein Text, keine Tastenkürzel |

`jitter_percent` macht zusätzlich den Abstand unregelmäßig, aber nur **kürzer** als eingestellt, damit die
Leerlaufgrenze nie überschritten wird.

Bewusste Grenzen:
- **Keine echten Buchstaben.** Text würde im gerade fokussierten Feld landen (Adresszeile, Eingabefelder,
  Backtest-Parameter) oder Tastenkürzel auslösen. Darum nur F13–F24, die auf normalen Tastaturen fehlen.
- **Scrollen** wirkt auf das Fenster unter dem Mauszeiger (Windows-Standard „inaktive Fenster scrollen“).
  Steht eine Seite ganz oben/unten, kann der Hin-Schritt ins Leere gehen und der Rück-Schritt die Seite minimal
  verschieben. Über einem fokussierten Zahlenfeld kann das Rad den Wert kurz ändern (netto zurück). Wer das
  nicht möchte: Variante abhaken.
- **Mausbewegung** kann Hover-Effekte (Tooltips, Menüs) kurz auslösen.

## Browser-Test

Bei `signal: browse` startet nach jedem Abstand (Sie waren so lange nicht aktiv) ein **Durchlauf**:

1. Browser nach vorne holen: Ist gerade kein Browser vorn (z. B. Taskleiste, Infobereich oder Desktop), wird das
   zuletzt benutzte Browserfenster automatisch nach vorne geholt (auch aus der Minimierung). Gibt es keins, zeigt
   das gelbe Symbol „Pausiert, kein Browserfenster gefunden (vorne: programm.exe)“. Ein eigener Browser, der nicht
   erkannt wird, kommt mit seinem Programmnamen in `browse_processes`.
   **Inkognito-/InPrivate-Fenster werden nie benutzt:** Liegt eins vorne, wird stattdessen ein normales
   Browserfenster genommen; gibt es nur Inkognito-Fenster, wird der Durchlauf übersprungen.
2. **Eigenes normales Fenster öffnen** (nur Strg+N, nie Inkognito). Ihre vorhandenen Fenster und Tabs werden nie
   bedient, geschlossen oder verändert – alles Weitere passiert nur im neuen Testfenster und seinen eigenen Tabs.
   Sollte das neue Fenster doch ein Inkognito-Fenster sein, wird es sofort wieder geschlossen und der Durchlauf
   abgebrochen.
3. **Wie ein Mensch surfen** – jede Runde ist eine kleine Sitzung einer „Person“ mit festen Gewohnheiten:
   - **Stimmung** ruhig / normal / hektisch (Tempo von Lesen und Tippen) und eigene **Lesedauer** und **Neugier**,
   - **Lieblings-Tastenkürzel**: dieselbe Taste für die Adresszeile (meist Strg+L) und fürs Tab-Wechseln, nur
     ab und zu eine andere – Menschen wechseln nicht bei jeder Suche die Methode,
   - **Anliegen mit rotem Faden**: z. B. „wetter leipzig“ → Ergebnis öffnen, lesen, zurück → zweites Ergebnis →
     „wetter leipzig 14 tage“ → „regenradar leipzig“ → neuer Tab für ein Nebenthema („hotel dresden“),
   - **typischer Ablauf**: Ergebnisliste überfliegen, Treffer anklicken (Maus fährt im Bogen hin, zögert kurz,
     schießt manchmal minimal übers Ziel), lesen (Scroll-Schübe aus mehreren Raddrehungen, Lesepausen, mal ein
     Stück zurück, Maus wandert mit), oft zurück zur Liste; Treffer für später per Strg+Klick im Hintergrund-Tab
     öffnen und danach dorthin wechseln und lesen; ab und zu abgelenkt (Pause bis 45 s),
   - **Pausen log-normal** statt gleichmäßig: meist kurz, manchmal deutlich länger – wie echte Menschen,
   - **seltene Browserfunktionen** (Zoom, Verlauf, Vollbild, Menü, Quelltext …) höchstens 2 pro Durchlauf und
     jede nur einmal (zusammen unter 10 % aller Aktionen).
   1/3 bis volle `browse_actions_max` Aktionen je Durchlauf.
4. **Aufräumen:** alle eigenen Fenster mit Strg+W schließen (geprüft über das Fensterhandle), Mauszeiger zurück.

Suchanfragen: rund 20 Themen (Wetter, Rezepte, Fußball, Bahn, Urlaub, Technik, Finanzen, Gesundheit, Haushalt,
Garten, Wissensfragen, Freizeit, Job, Behörden, Auto, Tiere, Programmieren, Englisch, Rechnen/Umrechnen, Zahlen)
mit Startanfrage, Verfeinerungen und verwandten Fragen, Städten, Vereinen und Jahren. Zahlen so, wie Menschen sie
tippen (`17 * 23`, `83 km in meilen`, `19 prozent von 250`, Postleitzahlen, Jahreszahlen). Etwa jede achte Anfrage
hat einen absichtlichen, nicht korrigierten Tippfehler (testet die Rechtschreibkorrektur). **Tipprhythmus**:
unregelmäßig, nach Leerzeichen länger, Zahlen und Umlaute langsamer, Doppelbuchstaben schneller, manchmal kurzes
Überlegen; Vertipper werden wie bei Menschen oft erst ein, zwei Zeichen später bemerkt und mit mehreren
Rücktasten korrigiert. Getippt wird per Unicode, unabhängig vom Tastaturlayout.

| ID | Ablauf (Tastenkürzel) |
|---|---|
| `suche` | neues Anliegen: Adresszeile (Lieblingstaste), Anfrage tippen, Enter – manchmal nur anfangen, Vorschlag mit ↓ wählen; Ergebnisliste überfliegen |
| `suche_verfeinern` | gleiches Anliegen genauer oder verwandt suchen |
| `ergebnis_oeffnen` | Treffer anklicken, lesen, oft Alt+← zurück zur Liste |
| `im_tab_oeffnen` | 1–2 Treffer per Strg+Klick im Hintergrund-Tab öffnen (später per `tab_wechseln` gelesen) |
| `suche_abbrechen` | Adresszeile, halbe Anfrage tippen, Esc |
| `www_com` | Strg+L, bekannter Name (wikipedia, github …), Strg+Enter |
| `neuer_tab`, `tab_schliessen`, `tab_duplizieren` | Strg+T (meist mit neuer Suche), Strg+W (nie den letzten Tab), Strg+Shift+K |
| `tab_wechseln` | Lieblingstaste (Strg+Tab, Strg+Bild↓ …), Strg+1–8; vorgemerkte Treffer werden gelesen |
| `neues_fenster`, `fenster_schliessen` | Strg+N, schließen per Strg+W (max. 2 eigene Fenster) |
| `zurueck_vor`, `startseite`, `neu_laden` | Alt+←/→, Alt+Home, F5 / Strg+R / Shift+F5 (manchmal sofort Esc) |
| `lesen_scrollen`, `tastatur_scrollen` | Scroll-Schübe mit Lesepausen; Strg+F6, Leertaste, Pfeile, Bild↓/↑, Home, Ende |
| `klicken` | auf einer Seite einem Link folgen |
| `auf_seite_suchen` | Strg+F, Wort aus der Suche tippen, Enter / Strg+G / F3, Esc |
| `zoom`, `vollbild`, `reader`, `caret_browsing` | selten: Strg+Plus (danach immer Strg+0); F11 hin und zurück; F9 hin und zurück; F7 + Esc |
| `verlauf`, `downloads`, `favoriten`, `sammlungen`, `seitenleiste_suche` | selten: Strg+H, Strg+J, Strg+Shift+O, Strg+Shift+Y, Strg+Shift+E – danach wieder zu |
| `favoritenleiste`, `favoritenleiste_fokus` | selten: Strg+Shift+B zweimal; Alt+Shift+B, Pfeile, Esc |
| `quelltext` | selten: Strg+U, kurz lesen, Strg+W |
| `stumm`, `vorlesen` | selten: Strg+M zweimal; Strg+Shift+U starten und wieder stoppen |
| `fokus_bereiche`, `menue`, `kontextmenue` | selten: F6, Shift+F6, Tab; Alt / F10; Shift+F10 – jeweils Esc |
| `pdf` | selten: Strg+\, Strg+[, Strg+] (wirkt nur in PDFs) |
| `pause` | abgelenkt: meist ein paar Sekunden, manchmal bis 45 s |

**Nie verwendet** (fest gesperrt): Alt+F4, Strg+Shift+W, Strg+Shift+Entf, Strg+P, Strg+Shift+P, Strg+S, Strg+O,
F12, Strg+Shift+I, Alt+Shift+I, Strg+D, Strg+Shift+D, Strg+Shift+V, Strg+Shift+L (Zwischenablage),
**Strg+Shift+N** (Inkognito/InPrivate), **Strg+Shift+T** (würde browserweit den zuletzt geschlossenen Tab
wiederherstellen – evtl. einen von Ihnen) und **Strg+Shift+A** (Tab-Suche springt auch in fremde Fenster).
Die früheren Aktionen `inprivate_fenster` und `tab_wiederherstellen` gibt es nicht mehr; stehen sie noch in
`browse_exclude`, werden sie still ignoriert.

**Sicherheit:**
- Vor jedem Schritt wird geprüft, dass das eigene Testfenster im Vordergrund ist. Liegt ein fremdes Fenster vorn,
  bekommt es keine Eingabe: das eigene Testfenster wird wieder nach vorne geholt, klappt das nicht, wird der
  Durchlauf abgebrochen. Das fremde Fenster bleibt unberührt.
- Ist kein eigenes Testfenster mehr offen, werden keine Tasten, Klicks, Scrolls oder Texte mehr gesendet.
- Öffnet eine Seite **direkt nach einem eigenen Klick** (bis 8 s) ein Popup-Fenster, wird es geschlossen. Neue
  Fenster ohne eigenen Klick (z. B. Link aus einer Mail, anderes Programm) werden nie angefasst.
- **Sobald Sie Maus oder Tastatur benutzen, bricht der Durchlauf sofort ab** (Leerlaufzähler, eigene Eingaben
  werden herausgerechnet). Offen gebliebene Testfenster werden beim nächsten Durchlauf geschlossen – aber nur,
  wenn ihr Titel unverändert ist. Haben Sie das Fenster inzwischen benutzt, bleibt es offen.
- Ausschalten, Bildschirmsperre und Beenden stoppen den Durchlauf ebenfalls.

**Erweiterungs-Zähler:** Vor und nach jedem Durchlauf wird die Zahl auf einem Erweiterungs-Symbol oben rechts
gelesen – zuerst über UI Automation (Name/Tooltip des Buttons), sonst per Windows-Texterkennung (OCR) auf dem
Button. Tooltip: `Zähler 698 → 712, …`; ist er nicht gestiegen, steht `Zähler nicht gestiegen` als Auffälligkeit
im Protokoll. `python -m awaketoggle --selftest` listet alle gefundenen Buttons mit Namen – den passenden Namen
in `badge_extension` eintragen, falls automatisch die falsche Erweiterung gewählt wird.

**Probleme sehen:** Im Protokoll stehen Start, Ende und Dauer jedes Durchlaufs sowie Auffälligkeiten als `WARNING`:
`Langsam: 7.3 s (Suche 'wetter 4711')`, `Keine Reaktion nach 15 s (...)` (Fenstertitel hat sich nach Enter nicht
geändert), Popups, nicht erkannte neue Fenster. Mit `verbose_log: true` wird jede einzelne Aktion protokolliert.
Der Tooltip zeigt das Ergebnis des letzten Durchlaufs.

Abgestimmt auf die Edge-Tastenkürzel (Sammlungen, Plastischer Reader). Mit Chrome & Co. funktioniert der
Großteil ebenso; nicht vorhandene Kürzel bewirken dort einfach nichts. Hinweis: Zoomstufen merkt sich der Browser pro
Website, deshalb endet jede Zoom-Aktion mit Strg+0.

## Weg-Modus (Helligkeit + Stromsparen)

Sobald das Programm arbeitet (erstes Signal bzw. erster Browser-Test-Durchlauf, weil Sie lange genug nichts getan
haben), schaltet es:

- **Helligkeit auf 0 %** (`away_brightness`) – eingebaute Laptop-Anzeige über WMI, externe Monitore über DDC/CI
  (muss im Monitor-Menü aktiviert sein; manche Monitore/Adapter unterstützen das nicht),
- **Stromsparmodus an** (`away_energy_saver`) – Windows-Energiesparmodus (Schwelle auf 100 %) und Energiemodus
  „Beste Energieeffizienz“.

Zwischen den Durchläufen bleibt das so. **Sobald Sie Maus oder Tastatur benutzen** (geprüft alle 0,3 s, eigene
Eingaben des Programms werden herausgerechnet), geht es sofort zurück: **Helligkeit 50 %** (`back_brightness`),
Stromsparmodus aus (Ihre vorherige Einstellung wird wiederhergestellt). Ebenso beim Ausschalten und Beenden.
Wird das Programm hart beendet (Task-Manager), setzt es beim nächsten Start alles zurück (`away_state.json`).
Keine Administratorrechte nötig. Im Protokoll steht, welche Monitore sich einstellen ließen.

Hinweis: Am Desktop-PC ohne Akku kann der Windows-Energiesparmodus je nach Windows-Version wirkungslos sein;
der Energiemodus „Beste Energieeffizienz“ wirkt trotzdem. Was geklappt hat, steht im Protokoll.

## Funktionsweise

- **Wach halten:** `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)` im
  Hintergrund-Thread, solange aktiv. Verhindert Ruhezustand und Abschalten des Bildschirms.
  Hinweis: Laut Microsoft hält dieser Aufruf den **Bildschirmschoner** nicht auf; das erledigt das Eingabesignal,
  solange dessen Abstand kürzer ist als die Bildschirmschoner-Wartezeit.
- **Signal:** `SendInput` – Maus relativ +1/−1 Pixel (Position wird danach geprüft und ggf. zurückgesetzt),
  F15 drücken/loslassen oder eine der Zufallsvarianten.
- **Intelligentes Pausieren:** Vor jedem Signal wird `GetLastInputInfo` gelesen. Kam die letzte Eingabe von Ihnen
  und liegt sie weniger als den Abstand zurück, wird nichts gesendet; der nächste Versuch erfolgt genau dann,
  wenn Ihre Eingabe den Abstand erreicht. Eigene Signale werden erkannt und nicht mit Ihren Eingaben verwechselt.
- **Gesperrter Bildschirm:** Erkennung über Sitzungsereignisse (`WTSRegisterSessionNotification`) und den
  Namen des Eingabedesktops. Dann Status „Pausiert, Bildschirm gesperrt“, es wird nichts gesendet.
- **Signal ohne Wirkung** (z. B. RDP-Fenster minimiert): Nach jedem Signal wird geprüft, ob sich der
  Leerlaufzähler zurückgesetzt hat. Wenn nicht: gelbes Symbol, „Pausiert, Signal ohne Wirkung“.
- **Sauberes Beenden:** Wachhalten wird aufgehoben bei *Beenden*, Abmelden/Herunterfahren (`WM_ENDSESSION`),
  Konsolen-/Signal-Ereignissen und über `atexit`. Bei hartem Abbruch gibt Windows den Zustand ohnehin frei,
  weil er an den Thread gebunden ist.
- **Nur eine Instanz:** benannter Mutex `Local\AwakeToggle.SingleInstance`.
- **Ressourcen:** Hintergrund-Thread wartet mit `threading.Event.wait()`, keine Abfrageschleife.
  Kein Netzwerk, keine Registry, keine Administratorrechte.

## Selbst bauen

Voraussetzung: Windows, Python 3.12.

```powershell
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q tests          # Logik-Tests
python -m awaketoggle --selftest   # prüft die echten Win32-Aufrufe (zeigt auch das Vordergrundprogramm)
python -m awaketoggle              # direkt aus dem Quelltext starten
.\tools\build.cmd                  # erzeugt dist/AwakeToggle.exe (umgeht die Skript-Sperre von PowerShell)
```

## Release erstellen

GitHub Actions (`.github/workflows/build.yml`) baut bei jedem Push auf `main` und bei Pull Requests
(exe als Artefakt). Bei einem Tag `v*` wird zusätzlich ein Release mit `AwakeToggle.exe` und Prüfsumme veröffentlicht:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

Version im Code: `awaketoggle/__init__.py`.

## Phase 4: Test mit Power Browser

1. `verbose_log` auf `true`, Abstand kürzer als die Leerlaufgrenze von Power Browser einstellen.
2. **Maus oder F15?** `tools/eingabetest.html` in Power Browser öffnen (falls er lokale Dateien lädt) und
   sehen, ob `mousemove` bzw. `keydown key="F15"` ankommt. Die Mausbewegung kommt nur an, wenn der Zeiger
   über dem Browserfenster liegt; F15 nur, wenn der Browser den Tastaturfokus hat. Danach mit der echten
   Leerlauferkennung gegenprüfen. Wertet sie nur Tastatur aus → Signal auf F15.
3. **RAM:** Task-Manager → Details → Spalte „Arbeitsspeicher (privater Arbeitssatz)“. Die onefile-exe
   erscheint als zwei Prozesse `AwakeToggle.exe` (kleiner Entpacker + eigentliches Programm); beide addieren.
   Ziel: unter 25 MB, gemessen während der Backtest läuft.
4. **Ruhezustand:** aktiv schalten, `powercfg /requests` in einer Admin-Konsole – AwakeToggle sollte unter
   SYSTEM und DISPLAY erscheinen. Nach dem Ausschalten muss der Eintrag verschwinden.
5. **Bildschirmsperre:** `Win+L` → Symbol wird gelb, Protokoll „Sitzungsereignis: gesperrt“; nach dem
   Entsperren wieder grün.
6. **RDP minimiert:** prüfen, ob „Signal ohne Wirkung“ erscheint oder die Eingabe doch wirkt.

## Deinstallation

Menü → *Mit Windows starten* abschalten, *Beenden*, dann `AwakeToggle.exe` und den Ordner
`%LOCALAPPDATA%\AwakeToggle` löschen.

## Hinweis

Robuster als jede Eingabe von außen ist ein einstellbarer Timeout direkt in Power Browser.
