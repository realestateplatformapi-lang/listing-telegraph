$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "WINDOWS_CONFIG.ps1")
$PidFile = Join-Path $InstallRoot "cloudflared.pid"
if (Test-Path $PidFile) { $TunnelPid = Get-Content $PidFile; Stop-Process -Id $TunnelPid -Force -ErrorAction SilentlyContinue; Remove-Item $PidFile -Force }
Write-Host "Public tunnel stopped."
