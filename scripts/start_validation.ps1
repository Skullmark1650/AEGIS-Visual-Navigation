param([Parameter(Mandatory=$true)][ValidateSet('stationary','horizontal','vertical','rotation','low-light','low-texture','rapid-motion','feature-loss','network-interruption','repeat-path')][string]$Experiment,
      [int]$DurationSeconds = 120)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$aegisValidationName = $Experiment + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
$aegisRecording = 'data/validation/' + $aegisValidationName
Write-Host ('Validation recording: ' + $aegisRecording)
& "$PSScriptRoot/start_stream.ps1" -Dashboard -DurationSeconds $DurationSeconds -RecordingDirectory $aegisRecording -Experiment $Experiment
if ($LASTEXITCODE -ne 0) { throw 'Validation camera run failed; inspect launcher logs' }
& .\.venv\Scripts\python.exe -m laptop.validation --recording $aegisRecording --output ('results/reports/' + $aegisValidationName + '-validation.json')
if ($LASTEXITCODE -ne 0) { throw 'Offline validation failed; raw images and telemetry preserved' }
