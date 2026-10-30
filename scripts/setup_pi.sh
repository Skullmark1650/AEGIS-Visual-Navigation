#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
# Prerequisites: OS-managed python3-picamera2 and python3-venv.
python3 -c 'import picamera2'
python3 -m venv --system-site-packages .venv
.venv/bin/python scripts/verify_environment.py --role pi --output results/reports/pi-environment.json
