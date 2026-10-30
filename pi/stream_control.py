"""Start/stop only the AEGIS server registered in this repository."""
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PID = ROOT / "results/server.pid"


def server_pid():
    if not PID.exists():
        return None
    pid = int(PID.read_text().strip())
    try:
        command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    except FileNotFoundError:
        return None
    expected = str(ROOT / "pi/camera_server.py").encode()
    if expected not in command:
        raise RuntimeError("PID file does not identify this project's server; inspect it manually")
    return pid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "status"])
    args = parser.parse_args()
    pid = server_pid()
    if args.action == "status":
        print(f"Server PID {pid}" if pid else "Server stopped")
        return 0
    if args.action == "stop":
        if pid:
            os.kill(pid, signal.SIGTERM)
            for _ in range(100):
                if not PID.exists():
                    print("Server stopped cleanly")
                    return 0
                time.sleep(.1)
            raise RuntimeError("Server did not stop within 10 seconds; inspect results/server.log")
        print("Server already stopped")
        return 0
    if pid:
        print(f"Server already running: {pid}")
        return 0
    (ROOT / "results").mkdir(exist_ok=True)
    with (ROOT / "results/server.log").open("a", encoding="utf-8") as log:
        child = subprocess.Popen([sys.executable, str(ROOT / "pi/camera_server.py"),
                                  "--config", "configs/stream.json"], cwd=ROOT,
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                 start_new_session=True)
    for _ in range(50):
        if child.poll() is not None:
            raise RuntimeError("Server exited; inspect results/server.log")
        if PID.exists() and PID.read_text().strip() == str(child.pid):
            time.sleep(1)
            if child.poll() is None:
                print(f"Started AEGIS server: {child.pid}")
                return 0
        time.sleep(.1)
    raise RuntimeError("Server startup timed out; inspect results/server.log")


if __name__ == "__main__":
    raise SystemExit(main())
