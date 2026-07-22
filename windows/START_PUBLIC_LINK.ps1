$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "WINDOWS_CONFIG.ps1")
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) { throw "cloudflared is missing. Run: winget install Cloudflare.cloudflared" }
$PidFile = Join-Path $InstallRoot "cloudflared.pid"
$LogRoot = Join-Path $InstallRoot "logs"
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$Process = Start-Process -FilePath "cloudflared" -ArgumentList @("tunnel","--url","http://127.0.0.1:$LocalPort","--no-autoupdate") -WindowStyle Hidden -RedirectStandardOutput (Join-Path $LogRoot "cloudflared.out.log") -RedirectStandardError (Join-Path $LogRoot "cloudflared.err.log") -PassThru
Set-Content $PidFile $Process.Id
Write-Host "Public tunnel started. After 5-10 seconds, find the trycloudflare.com URL in $LogRoot\cloudflared.err.log"
