$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$dest = Join-Path $env:LOCALAPPDATA "Programs\AwakeToggle"
$exe = Join-Path $dest "AwakeToggle.exe"
$links = @(
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "AwakeToggle.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Programs")) "AwakeToggle.lnk")
)
$startupLink = Join-Path ([Environment]::GetFolderPath("Startup")) "AwakeToggle.lnk"

function Stop-AwakeToggle {
    Get-Process AwakeToggle -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-CimInstance Win32_Process -Filter "Name like 'python%'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "awaketoggle|$([regex]::Escape((Join-Path $root 'main.py')))" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Milliseconds 800
}

function New-Link($path, $target, $arguments, $workdir, $icon) {
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($path)
    $s.TargetPath = $target
    $s.Arguments = $arguments
    $s.WorkingDirectory = $workdir
    if ($icon) { $s.IconLocation = $icon }
    $s.Description = "AwakeToggle"
    $s.Save()
}

Write-Host "1/4 Python-Pakete installieren ..." -ForegroundColor Cyan
python -m pip install --disable-pip-version-check -q -r requirements.txt -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "pip fehlgeschlagen - ist Python 3.12 installiert und 'python' im PATH?" }

Write-Host "2/4 AwakeToggle.exe bauen (dauert 1-2 Minuten) ..." -ForegroundColor Cyan
$built = $true
try { & (Join-Path $PSScriptRoot "build.ps1") } catch { $built = $false; Write-Warning "exe-Bau fehlgeschlagen: $_" }

Write-Host "3/4 Laufendes AwakeToggle beenden und installieren ..." -ForegroundColor Cyan
Stop-AwakeToggle
if ($built) {
    New-Item -ItemType Directory -Force $dest | Out-Null
    Copy-Item (Join-Path $root "dist\AwakeToggle.exe") $exe -Force
    $target, $arguments, $workdir, $icon = $exe, "", $dest, "$exe,0"
} else {
    $py = (Get-Command python).Source
    $pyw = Join-Path (Split-Path $py) "pythonw.exe"
    if (-not (Test-Path $pyw)) { $pyw = $py }
    $ico = Join-Path $root "build\awaketoggle.ico"
    $target, $arguments, $workdir = $pyw, "`"$(Join-Path $root 'main.py')`"", $root
    $icon = if (Test-Path $ico) { $ico } else { "" }
    Write-Warning "Nutze stattdessen pythonw.exe (ohne Konsolenfenster) direkt aus $root"
}

Write-Host "4/4 Verknüpfungen auf Desktop und im Startmenü anlegen ..." -ForegroundColor Cyan
foreach ($l in $links) { New-Link $l $target $arguments $workdir $icon }
if (Test-Path $startupLink) { New-Link $startupLink $target $arguments $workdir $icon; Write-Host "   Autostart-Verknüpfung aktualisiert" }

$startArgs = @{ FilePath = $target; WorkingDirectory = $workdir }
if ($arguments) { $startArgs.ArgumentList = $arguments }
Start-Process @startArgs
Write-Host ""
Write-Host "Fertig. AwakeToggle läuft jetzt im Infobereich (Pfeil ^ unten rechts in der Taskleiste)." -ForegroundColor Green
Write-Host "Starten künftig per Desktop-Symbol 'AwakeToggle' oder Startmenü - VS Code/Terminal wird nicht gebraucht."
Write-Host "Mit Windows starten: Rechtsklick aufs Symbol -> 'Mit Windows starten'."
