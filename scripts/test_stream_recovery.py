"""Real-camera integration test: interrupt only this test's SSH forward."""
import argparse
import csv
import json
import socket
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path("results/reports/phase1-recovery.json"))
    parser.add_argument("--features", choices=["none", "shi-tomasi", "orb", "both"], default="none")
    parser.add_argument("--tracking", action="store_true")
    args = parser.parse_args()
    if args.report.exists():
        parser.error("Choose a new report name")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    # Do not terminate or reuse any unrelated listener.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 8766))
    command = ["ssh", "-N", "-o", "ExitOnForwardFailure=yes", "-L",
               "127.0.0.1:8766:127.0.0.1:8765", "aegis-pi"]
    tunnel = None
    client = None
    with args.report.with_suffix(".log").open("w", encoding="utf-8") as log:
        try:
            tunnel = subprocess.Popen(command, stdout=log, stderr=log)
            time.sleep(1)
            if tunnel.poll() is not None:
                raise RuntimeError("Test tunnel did not start; inspect test log")
            client_command = [sys.executable, "laptop/camera_client.py",
                "--url", "http://127.0.0.1:8766", "--headless", "--duration", "25",
                "--features", args.features,
                "--report", str(args.report)]
            if args.tracking:
                client_command.append("--tracking")
            client = subprocess.Popen(client_command, stdout=log, stderr=log)
            time.sleep(6)
            interrupted = time.monotonic()
            tunnel.terminate()
            tunnel.wait(timeout=5)
            time.sleep(3)
            restored = time.monotonic()
            tunnel = subprocess.Popen(command, stdout=log, stderr=log)
            client.wait(timeout=35)
            if client.returncode != 0:
                raise RuntimeError("Receiver failed; inspect log")
        finally:
            for process in [client, tunnel]:
                if process is not None and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
    summary = json.loads(args.report.read_text(encoding="utf-8"))
    with args.report.with_suffix(".csv").open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    maximum_gap = max(float(b["elapsed_s"])-float(a["elapsed_s"])
                      for a, b in zip(rows, rows[1:]))
    tracking_reset = not args.tracking or summary.get("tracking", {}).get("reset_reasons", {}).get("frame_gap", 0) >= 1
    summary["recovery_test"] = {
        "method": "Terminated owned SSH forward for three seconds; Pi camera kept running",
        "forward_restart_delay_s": restored-interrupted,
        "maximum_receive_gap_s": maximum_gap,
        "tracking_reset_on_gap": tracking_reset if args.tracking else None,
        "passed": summary["connections"] >= 2 and summary["connection_errors"] >= 1 and tracking_reset}
    args.report.write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["recovery_test"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
