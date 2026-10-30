param([int]$DurationSeconds = 3600,
      [ValidateSet('none','shi-tomasi','orb','both')][string]$Features = 'both',
      [switch]$Tracking,
      [string]$OdometryCalibration = "",
      [switch]$Dashboard,
      [string]$RecordingDirectory = "",
      [string]$Experiment = "unlabeled",
      [string]$StatusFile = "",
      [string]$StopFile = "")
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force -Path 'results/reports' | Out-Null
if ($Dashboard -and -not $OdometryCalibration) { $OdometryCalibration = 'results/calibration/phase4-reviewed-camera.json' }
if ($OdometryCalibration -and -not (Test-Path -LiteralPath $OdometryCalibration)) {
    throw 'Calibration not found. Follow docs/CALIBRATION_GUIDE.md and supply -OdometryCalibration with your reviewed file.'
}
if ($DurationSeconds -lt 1) { throw 'Duration must be positive' }
if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8765 is already in use. Stop the existing stream before starting another.'
}
& ssh aegis-pi 'cd ~/AEGIS && .venv/bin/python pi/stream_control.py start'
if ($LASTEXITCODE -ne 0) { throw 'Pi camera server did not start' }
if ($Dashboard -and -not $OdometryCalibration) { $OdometryCalibration = 'results/calibration/phase4-reviewed-camera.json' }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$tunnel = Start-Process -FilePath 'ssh.exe' -ArgumentList @('-N','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=10','-L','127.0.0.1:8765:127.0.0.1:8765','aegis-pi') -WindowStyle Hidden -PassThru -RedirectStandardError "results/reports/tunnel-$stamp.log"
try {
    Start-Sleep -Seconds 1
    if ($tunnel.HasExited) { throw 'SSH forward failed; inspect tunnel log' }
    if ($OdometryCalibration) { $Tracking = $true }
    if ($Tracking) { $Features = 'none' }
    $clientArguments = @('laptop/camera_client.py','--duration',"$DurationSeconds",'--features',$Features,'--report',"results/reports/viewer-$stamp.json")
    if ($Tracking) { $clientArguments += '--tracking' }
    if ($Dashboard) { $clientArguments += '--dashboard' }
    if ($RecordingDirectory) { $clientArguments += @('--record-directory', $RecordingDirectory, '--experiment', $Experiment) }
    if ($StatusFile) { $clientArguments += @('--status-file', $StatusFile) }
    if ($StopFile) { $clientArguments += @('--stop-file', $StopFile) }
    if ($OdometryCalibration) { $clientArguments += @("--odometry", $OdometryCalibration) }
    & .\.venv\Scripts\python.exe @clientArguments
} finally {
    if (-not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id }
    & ssh aegis-pi 'cd ~/AEGIS && .venv/bin/python pi/stream_control.py stop'
}
