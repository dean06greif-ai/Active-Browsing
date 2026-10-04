# AwakeToggle Fix (Repo dean06greif-ai/Active-Browsing, Branch conflict_031026_1038)
Problem: Browser-Test erkannte eigenen Browser (power.exe) nicht, explorer.exe als "vorne", keine kurzen Abstände.
## Erledigt (Juni 2026)
- power.exe + "power*"-Namen als Browser erkannt (außer PowerShell/PowerToys)
- find_browser: Z-Reihenfolge, ignoriert Explorer/Shell, Tool- und unsichtbare (cloaked) Fenster, eigenes Programm; Fallback oberstes Programmfenster
- Abstand 5/10/15 s + "Eigener Wert eingeben" (1-3600 s), Menüpunkt "Jetzt testen"
- 50 pytest-Tests grün; Code in /app/awaketoggle_fix (+ fix.patch)
## Backlog
- Auf echtem Windows mit Power Browser prüfen (--selftest zeigt erkanntes Fenster)
## Erweiterungs-Zähler (Juni 2026)
- badge.py (Zahl parsen/vergleichen), badge_win.py (UI Automation via comtypes, Fallback Windows-OCR per PowerShell auf Button-Bereich)
- Vor/nach jedem Browser-Test lesen, Tooltip "Zähler X → Y", Auffälligkeit wenn nicht gestiegen
- config: badge_read (true), badge_extension (""=auto); Tray-Schalter; --selftest listet Buttons
- 52 Tests grün; auf echtem Windows ungetestet
