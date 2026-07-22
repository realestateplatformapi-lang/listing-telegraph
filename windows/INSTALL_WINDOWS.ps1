param([string]$SourceRoot = (Split-Path $PSScriptRoot -Parent))
$ErrorActionPreference = "Stop"
$ConfigPath = Join-Path $PSScriptRoot "WINDOWS_CONFIG.ps1"
if (-not (Test-Path $ConfigPath)) {
    Copy-Item (Join-Path $PSScriptRoot "WINDOWS_CONFIG.example.ps1") $ConfigPath
    Write-Host "Created $ConfigPath. Fill in CHANGE_ME values, then run this script again."
    exit 1
}
. $ConfigPath
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python is missing. Install Python 3.12+ from python.org and enable Add Python to PATH." }
$AppRoot = Join-Path $InstallRoot "app"
$DataRoot = Join-Path $InstallRoot "data"
$LogRoot = Join-Path $InstallRoot "logs"
New-Item -ItemType Directory -Force -Path $AppRoot,$DataRoot,$LogRoot | Out-Null
Copy-Item (Join-Path $SourceRoot "app.py") $AppRoot -Force
Copy-Item (Join-Path $SourceRoot "index.html") $AppRoot -Force
Copy-Item (Join-Path $SourceRoot "requirements.txt") $AppRoot -Force
if (-not (Test-Path (Join-Path $InstallRoot "venv"))) { & py -3 -m venv (Join-Path $InstallRoot "venv") }
$Python = Join-Path $InstallRoot "venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $AppRoot "requirements.txt")
Write-Host "Installed KYIV ESTATE in $InstallRoot"
Write-Host "Next: run START_BLOCK3_HIDDEN.ps1"
