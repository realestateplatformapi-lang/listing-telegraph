$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "WINDOWS_CONFIG.ps1")
$PidFile = Join-Path $InstallRoot "block3.pid"
if (-not (Test-Path $PidFile)) { Write-Host "KYIV ESTATE is not running."; exit 0 }
$ServicePid = Get-Content $PidFile -ErrorAction SilentlyContinue
if ($ServicePid) { Stop-Process -Id $ServicePid -Force -ErrorAction SilentlyContinue }
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
Write-Host "KYIV ESTATE stopped."
