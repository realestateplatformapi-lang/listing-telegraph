$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "WINDOWS_CONFIG.ps1")
if ($MacHost -like "CHANGE_ME*") { throw "Set MacHost in WINDOWS_CONFIG.ps1." }
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) { throw "OpenSSH Client is missing. Install it in Windows Optional Features." }
$Stage = Join-Path $env:TEMP "kyiv-estate-sync"
Remove-Item $Stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
$Remote = "$MacUser@${MacHost}"
foreach ($Name in @("app.py","index.html","requirements.txt")) {
    & scp -i $SshKeyPath "$Remote`:$MacProjectPath/$Name" $Stage
    if ($LASTEXITCODE -ne 0) { throw "Failed to copy $Name from Mac." }
}
$AppRoot = Join-Path $InstallRoot "app"
New-Item -ItemType Directory -Force -Path $AppRoot | Out-Null
Copy-Item (Join-Path $Stage "*") $AppRoot -Force
if ($MacDataPath) {
    $DataStage = Join-Path $Stage "data"
    & scp -r -i $SshKeyPath "$Remote`:$MacDataPath" $DataStage
    if ($LASTEXITCODE -eq 0 -and (Test-Path $DataStage)) {
        New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot "data") | Out-Null
        Copy-Item (Join-Path $DataStage "*") (Join-Path $InstallRoot "data") -Recurse -Force
    }
}
Write-Host "Mac project and available data were copied to Windows. Restart KYIV ESTATE to load code changes."
