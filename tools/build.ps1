# Fehler über Exit-Codes prüfen: PyInstaller schreibt auch bei Erfolg viel nach stderr
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

python tools/make_icon.py build/awaketoggle.ico
if ($LASTEXITCODE -ne 0) { throw "Symbol konnte nicht erzeugt werden" }

python -m PyInstaller --noconfirm --clean --onefile --noconsole `
    --name AwakeToggle `
    --icon build/awaketoggle.ico `
    --hidden-import pystray._win32 `
    --collect-submodules comtypes `
    --exclude-module tkinter `
    --exclude-module unittest `
    --exclude-module pydoc `
    --exclude-module doctest `
    main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fehlgeschlagen" }

Get-Item dist/AwakeToggle.exe | Select-Object Name, Length
