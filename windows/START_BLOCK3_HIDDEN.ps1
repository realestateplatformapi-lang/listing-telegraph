$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "WINDOWS_CONFIG.ps1")
$Python = Join-Path $InstallRoot "venv\Scripts\python.exe"
$App = Join-Path $InstallRoot "app\app.py"
$PidFile = Join-Path $InstallRoot "block3.pid"
$LogRoot = Join-Path $InstallRoot "logs"
if (Test-Path $PidFile) {
    $ExistingPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($ExistingPid -and (Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue)) { Write-Host "KYIV ESTATE is already running: PID $ExistingPid"; exit 0 }
}
if (-not (Test-Path $Python)) { throw "Run INSTALL_WINDOWS.ps1 first." }
$env:PORT = [string]$LocalPort
$env:DATA_ROOT = Join-Path $InstallRoot "data"
$env:KYIV_ESTATE_LOGO_URL = $KyivEstateLogoUrl
$env:KYIV_ESTATE_LOGO_PATH = $KyivEstateLogoPath
$env:KYIV_ESTATE_PHONE = $KyivEstatePhone
$env:KYIV_ESTATE_URL = $KyivEstateUrl
$env:KYIV_ESTATE_INSTAGRAM = $KyivEstateInstagram
$env:KYIV_ESTATE_TELEGRAM = $KyivEstateTelegram
$env:KYIV_ESTATE_WHATSAPP = $KyivEstateWhatsApp
$env:KYIV_ESTATE_FACEBOOK = $KyivEstateFacebook
$env:KYIV_ESTATE_EMAIL = $KyivEstateEmail
$env:TELEGRAPH_ACCESS_TOKEN = $TelegraphAccessToken
$env:KYIV_ESTATE_AI_ENDPOINT = $AiEndpoint
$env:KYIV_ESTATE_AI_PACKAGES_ROOT = $AiPackagesRoot
$env:KYIV_ESTATE_SOURCE_LISTINGS_ROOT = $SourceListingsRoot
$env:KYIV_ESTATE_AI_REQUIRED = if ($AiRequired) { "true" } else { "false" }
$env:KYIV_ESTATE_AI_TIMEOUT_SECONDS = [string]$AiTimeoutSeconds
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$Process = Start-Process -FilePath $Python -ArgumentList @($App) -WorkingDirectory (Split-Path $App) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $LogRoot "block3.out.log") -RedirectStandardError (Join-Path $LogRoot "block3.err.log") -PassThru
Set-Content -Path $PidFile -Value $Process.Id
Start-Sleep -Seconds 2
try { $Health = Invoke-RestMethod "http://127.0.0.1:$LocalPort/health" -TimeoutSec 5; Write-Host "KYIV ESTATE is running: http://127.0.0.1:$LocalPort/" }
catch { throw "Service did not start. Check $LogRoot\block3.err.log" }
