param([int]$DurationSeconds = 3600,
      [string]$Dataset = '',
      [switch]$Resume)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force -Path 'results/reports' | Out-Null
if ($DurationSeconds -lt 1) { throw 'Duration must be positive' }
if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Close the previous viewer/SSH forward before starting calibration capture.'
}
& ssh aegis-pi 'cd ~/AEGIS && .venv/bin/python pi/stream_control.py start'
if ($LASTEXITCODE -ne 0) { throw 'Pi server could not start' }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
if (-not $Dataset) { $Dataset = "data/calibration/session-$stamp" }
$tunnel = Start-Process -FilePath 'ssh.exe' -ArgumentList @('-N','-o','ExitOnForwardFailure=yes','-L','127.0.0.1:8765:127.0.0.1:8765','aegis-pi') -WindowStyle Hidden -PassThru -RedirectStandardError "results/reports/calibration-tunnel-$stamp.log"
try {
    Start-Sleep -Seconds 1
    if ($tunnel.HasExited) { throw 'SSH forward failed' }
    Write-Output "Calibration dataset: $Dataset"
    $captureArguments = @('-m','laptop.calibration_capture','--dataset',$Dataset,'--duration',"$DurationSeconds")
    if ($Resume) { $captureArguments += '--resume' }
    & .\.venv\Scripts\python.exe @captureArguments
    if ($LASTEXITCODE -ne 0) { throw 'Calibration capture did not finish successfully' }
} finally {
    if (-not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id }
    & ssh aegis-pi 'cd ~/AEGIS && .venv/bin/python pi/stream_control.py stop'
}
