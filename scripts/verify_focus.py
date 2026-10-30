"""Measure reported lens stability through the real stream, without claiming sharpness."""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

# A script entry point must import the repository rather than assume installation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from laptop.camera_client import read_frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.frames < 10 or args.report.exists():
        parser.error("At least ten frames and an unused report path are required")
    values = []
    profiles = set()
    modes = set()
    started = time.monotonic()
    with urllib.request.urlopen(args.url+"/stream.mjpg", timeout=5) as stream:
        for _ in range(args.frames):
            headers, _ = read_frame(stream)
            values.append(float(headers["x-lens-position"]))
            profiles.add(headers["x-camera-profile-id"])
            modes.add(headers["x-focus-mode"])
    with urllib.request.urlopen(args.url+"/profile", timeout=5) as response:
        profile = json.load(response)
    target = profile["profile"]["lens_position"]
    report = {"frames": args.frames, "elapsed_s": time.monotonic()-started,
        "reported_lens_min": min(values), "reported_lens_max": max(values),
        "max_deviation_from_requested": max(abs(value-target) for value in values),
        "profile": profile, "passed": modes == {"manual"} and profiles == {profile["profile_id"]} and all(abs(value-target) <= .05 for value in values),
        "note": "Reported actuator control stability only. Target sharpness and real camera calibration still require a physical board."}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
