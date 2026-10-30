"""Capture one JPEG on the Pi; no preview or network server is started."""
from __future__ import annotations
import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

LOG = logging.getLogger("aegis.capture")


def capture(output: Path, width: int = 640, height: int = 480,
            warmup: float = 3.0) -> dict:
    if width <= 0 or height <= 0 or not 0 <= warmup <= 60:
        raise ValueError("Positive dimensions and warmup between 0 and 60 seconds required")
    if output.suffix.lower() not in {".jpg", ".jpeg"}:
        raise ValueError("Output must have .jpg or .jpeg extension")
    if output.exists() or output.with_suffix(".json").exists():
        raise FileExistsError("Choose a new output filename; existing results are preserved")
    # Lazy import allows argument validation and unit tests on Windows.
    from picamera2 import Picamera2
    output.parent.mkdir(parents=True, exist_ok=True)
    camera = Picamera2()
    started = time.monotonic()
    try:
        camera.configure(camera.create_still_configuration(main={"size": (width, height)}))
        camera.start(show_preview=False)
        time.sleep(warmup)
        metadata = camera.capture_file(str(output))
    finally:
        camera.close()
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Camera did not produce a nonempty image")
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "output": str(output.resolve()), "requested_size": [width, height],
              "bytes": output.stat().st_size,
              "elapsed_including_warmup_seconds": time.monotonic() - started,
              "metadata": metadata,
              "note": "Connectivity test only; not a streaming or accuracy benchmark"}
    output.with_suffix(".json").write_text(
        json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return report


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--warmup", type=float, default=3.0)
    args = parser.parse_args()
    try:
        report = capture(args.output, args.width, args.height, args.warmup)
    except KeyboardInterrupt:
        LOG.warning("Capture interrupted")
        return 130
    except Exception:
        LOG.exception("Capture failed: check camera connection, competing processes, and OS camera packages")
        return 1
    LOG.info("Saved %s (%s bytes)", report["output"], report["bytes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
