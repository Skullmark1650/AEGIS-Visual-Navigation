"""Read-only checks, plus an optional local JSON report. No network requests."""
from __future__ import annotations
import argparse
import importlib
import importlib.metadata
import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def inspect_environment(role: str) -> dict:
    if role not in {"pi", "laptop"}:
        raise ValueError("role must be pi or laptop")
    checks = {"python_supported": sys.version_info >= (3, 11),
              "virtual_environment": sys.prefix != sys.base_prefix,
              "git_available": shutil.which("git") is not None}
    report = {"role": role, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "executable": sys.executable,
              "system": platform.system(), "machine": platform.machine(),
              "checks": checks}
    if role == "pi":
        checks["linux"] = platform.system() == "Linux"
        checks["camera_utility"] = shutil.which("rpicam-still") is not None
        try:
            module = importlib.import_module("picamera2")
            report["picamera2_path"] = module.__file__
            report["picamera2_version"] = importlib.metadata.version("picamera2")
            checks["picamera2_import"] = True
        except Exception as exc:
            checks["picamera2_import"] = False
            report["picamera2_error"] = str(exc)
    else:
        checks["windows"] = platform.system() == "Windows"
        checks["ssh_available"] = shutil.which("ssh") is not None
    report["passed"] = all(checks.values())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", required=True, choices=["pi", "laptop"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = inspect_environment(args.role)
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
