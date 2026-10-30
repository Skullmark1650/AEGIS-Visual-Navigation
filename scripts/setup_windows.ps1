param([Parameter(Mandatory=$true)][string]$PythonExe)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& $PythonExe -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed' }
& .\.venv\Scripts\python.exe -m pip install -r laptop/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& .\.venv\Scripts\python.exe scripts/verify_environment.py --role laptop --output results/reports/windows-environment.json
if ($LASTEXITCODE -ne 0) { throw 'Environment verification failed' }
