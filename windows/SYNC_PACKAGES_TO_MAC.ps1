$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "WINDOWS_CONFIG.ps1")
if ($MacHost -like "CHANGE_ME*") { throw "Set MacHost in WINDOWS_CONFIG.ps1." }
$Packages = Join-Path $InstallRoot "data\packages"
if (-not (Test-Path $Packages)) { throw "No Windows packages found in $Packages" }
$Remote = "$MacUser@${MacHost}"
& ssh -i $SshKeyPath $Remote "mkdir -p '$MacDataPath/packages'"
if ($LASTEXITCODE -ne 0) { throw "Unable to prepare the Mac package directory." }
& scp -r -i $SshKeyPath (Join-Path $Packages "*") "$Remote`:$MacDataPath/packages/"
if ($LASTEXITCODE -ne 0) { throw "Package upload to Mac failed." }
Write-Host "Windows packages were copied to Mac."
