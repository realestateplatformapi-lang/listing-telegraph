$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$pidFile = Join-Path $root 'data\runtime\bridge-worker.pid'
$old = if (Test-Path -LiteralPath $pidFile) { Get-Process -Id ([int](Get-Content -LiteralPath $pidFile -Raw)) -ErrorAction SilentlyContinue }
if ($old) { Write-Output "Bridge worker already running: $($old.Id)"; exit 0 }
$process = Start-Process -FilePath 'D:\KyivEstateListingTelegraph\venv\Scripts\python.exe' -ArgumentList (Join-Path $root 'BRIDGE_WORKER.py') `
  -RedirectStandardOutput (Join-Path $root 'data\bridge-worker.log') `
  -RedirectStandardError (Join-Path $root 'data\bridge-worker-error.log') -PassThru -WindowStyle Hidden
$process.Id | Set-Content -LiteralPath $pidFile -Encoding ASCII
Write-Output "Railway AI bridge started: $($process.Id)"
