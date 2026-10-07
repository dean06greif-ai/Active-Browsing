$ErrorActionPreference = "Continue"
$root = Split-Path $PSScriptRoot -Parent
$dest = Join-Path $env:LOCALAPPDATA "Programs\AwakeToggle"

Get-Process AwakeToggle -ErrorAction SilentlyContinue | Stop-Process -Force
Get-CimInstance Win32_Process -Filter "Name like 'python%'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "awaketoggle|$([regex]::Escape((Join-Path $root 'main.py')))" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 800

foreach ($folder in "Desktop", "Programs", "Startup") {
    $l = Join-Path ([Environment]::GetFolderPath($folder)) "AwakeToggle.lnk"
    if (Test-Path $l) { Remove-Item $l -Force; Write-Host "Entfernt: $l" }
}
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force; Write-Host "Entfernt: $dest" }

$cfg = Join-Path $env:LOCALAPPDATA "AwakeToggle"
Write-Host ""
Write-Host "AwakeToggle wurde deinstalliert." -ForegroundColor Green
Write-Host "Einstellungen und Protokoll liegen noch in $cfg (bei Bedarf von Hand löschen)."
Write-Host "Falls der Bildschirm noch dunkel ist: Helligkeit über die Windows-Einstellungen hochstellen."
