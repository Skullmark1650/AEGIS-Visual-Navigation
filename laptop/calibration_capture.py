"""Guided capture of real checkerboard images from the existing SSH/MJPEG feed."""
from __future__ import annotations
import argparse
from argparse import Namespace
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
from pathlib import Path
import queue
import threading
import time
import urllib.request
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from .camera_client import Receiver
from .camera_calibration import BoardConfig, inspect_board, corner_distance, verify_profile

LOG = logging.getLogger("aegis.calibration.capture")


class CaptureSession:
    def __init__(self, directory: Path, board: BoardConfig, profile: dict, resume=False):
        verify_profile(profile)
        self.directory = directory
        self.board = board
        self.profile = profile
        self.corners = []
        if resume:
            self.manifest = json.loads((directory/"dataset.json").read_text(encoding="utf-8"))
            saved_profile = self.manifest["camera_profile"]
            verify_profile(saved_profile)
            if self.manifest["board"] != board.__dict__ or saved_profile["profile_id"] != profile["profile_id"]:
                raise ValueError("Saved board or camera/focus/crop profile does not match; images preserved")
            for index, view in enumerate(self.manifest["views"], 1):
                if view["file"] != f"view-{index:04d}.png":
                    raise ValueError("Unexpected saved image numbering")
                path = directory/view["file"]
                if hashlib.sha256(path.read_bytes()).hexdigest() != view["sha256"]:
                    raise ValueError(f"Saved image integrity check failed: {path.name}")
                with Image.open(path) as image:
                    if list(image.size) != profile["profile"]["image_size"]:
                        raise ValueError("Saved image resolution mismatch")
                points = np.asarray(view["corners"], np.float32)
                if points.shape != (board.columns*board.rows, 2) or not np.isfinite(points).all():
                    raise ValueError("Invalid saved corners")
                self.corners.append(points)
            LOG.info("Resumed %s verified views without modifying images", len(self.corners))
            return
        directory.mkdir(parents=True, exist_ok=False)
        self.manifest = {"kind": "aegis_real_camera_capture", "created_utc": datetime.now(timezone.utc).isoformat(),
            "board": board.__dict__, "camera_profile": profile, "views": [],
            "square_size_note": "Nominal printed square size only. Supply measured size explicitly at fitting."}
        self.write_manifest()

    def write_manifest(self):
        temporary = self.directory/"dataset.json.tmp"
        temporary.write_text(json.dumps(self.manifest, indent=2)+"\n", encoding="utf-8")
        temporary.replace(self.directory/"dataset.json")

    def save(self, image, corners, quality, frame):
        if corners is None or not quality["accepted"]:
            raise ValueError("Cannot save: "+"; ".join(quality["reasons"]))
        if frame["camera_profile_id"] != self.profile["profile_id"] or frame["focus_mode"] != "manual":
            raise ValueError("Camera profile changed; start a new dataset")
        if frame["lens_position"] is None or not math.isfinite(frame["lens_position"]) or abs(frame["lens_position"]-self.profile["profile"]["lens_position"]) > .05:
            raise ValueError("Manual lens position not confirmed")
        if list(image.size) != self.profile["profile"]["image_size"]:
            raise ValueError("Image size/profile mismatch")
        if any(corner_distance(corners, previous) < self.board.duplicate_rms_px for previous in self.corners):
            raise ValueError("View too similar: move or tilt the target more")
        name = f"view-{len(self.corners)+1:04d}.png"
        path = self.directory/name
        if path.exists(): raise FileExistsError(path)
        image.save(path)
        record = {"file": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "captured_utc": datetime.now(timezone.utc).isoformat(),
            "camera_profile_id": frame["camera_profile_id"], "focus_mode": frame["focus_mode"],
            "lens_position": frame["lens_position"], "frame_id": frame["frame_id"],
            "producer_session": frame["session"], "sensor_ns": frame["sensor_ns"],
            "quality": quality, "corners": corners.tolist()}
        self.manifest["views"].append(record)
        self.corners.append(corners.copy())
        self.write_manifest()
        return name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/calibration.json"))
    parser.add_argument("--duration", type=float, default=3600)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.duration <= 0: parser.error("Duration must be positive")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    board = BoardConfig.load(args.config)
    deadline = time.monotonic()+5
    while True:
        try:
            with urllib.request.urlopen(args.url+"/profile", timeout=3) as response:
                profile = json.load(response)
            break
        except OSError:
            if time.monotonic() >= deadline: raise
            time.sleep(.2)
    session = CaptureSession(args.dataset, board, profile, resume=args.resume)
    transport_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    receiver = Receiver(Namespace(url=args.url, duration=args.duration, report=args.dataset/f"transport-{transport_stamp}.json",
                                   snapshot=None, headless=False, features="none"))
    received = threading.Thread(target=receiver.run, daemon=True)
    received.start()
    previews = queue.Queue(maxsize=1)
    latest = None

    def detect_worker():
        while not receiver.stop.is_set():
            try:
                image, row = receiver.latest.get(timeout=.2)
            except queue.Empty:
                continue
            try:
                started = time.perf_counter()
                corners, quality = inspect_board(image, board)
                quality["detection_ms"] = (time.perf_counter()-started)*1000
                preview = np.asarray(image).copy()
                if corners is not None:
                    cv2.drawChessboardCorners(preview, (board.columns, board.rows), corners.reshape(-1, 1, 2), True)
                result = (image, row, corners, quality, Image.fromarray(preview))
                if previews.full():
                    try: previews.get_nowait()
                    except queue.Empty: pass
                previews.put_nowait(result)
            except Exception:
                LOG.exception("Checkerboard preview failed")
                receiver.stop.set()

    detector = threading.Thread(target=detect_worker, daemon=True)
    detector.start()
    root = tk.Tk()
    root.title("AEGIS — Phase 4 calibration capture")
    root.configure(bg="#101820")
    label = tk.Label(root, bg="#101820")
    label.pack()
    status = tk.Label(root, bg="#101820", fg="#a9e4dd", font=("Consolas", 10), wraplength=650)
    status.pack(padx=10, pady=8)
    notice = tk.StringVar(value="Show the printed target. S saves a valid view; Q closes. No automatic capture.")
    tk.Label(root, textvariable=notice, bg="#101820", fg="#ffd36c", wraplength=650).pack(padx=10, pady=6)

    def close():
        receiver.stop.set()
        root.destroy()

    def save(_=None):
        try:
            if latest is None: raise ValueError("Waiting for a detected frame")
            image, row, corners, quality, _ = latest
            if time.monotonic()-receiver.started-row["elapsed_s"] > 1.5:
                raise ValueError("Frame is stale; wait for a fresh live image")
            name = session.save(image, corners, quality, row)
            notice.set(f"Saved {name}. Change position, tilt, or distance before the next S.")
            LOG.info("Saved calibration view %s", name)
        except (ValueError, OSError) as exc:
            notice.set(str(exc))
        with (args.dataset/"capture-events.jsonl").open("a", encoding="utf-8") as file:
            file.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), "message": notice.get()})+"\n")

    def refresh():
        nonlocal latest
        try:
            latest = previews.get_nowait()
            image, row, corners, quality, preview = latest
            photo = ImageTk.PhotoImage(preview)
            label.configure(image=photo)
            label.image = photo
        except queue.Empty:
            pass
        count = len(session.manifest["views"])
        prompts = ["Center at medium size; check sharpness", "Cover left/right and upper/lower image regions",
                   "Tilt target left/right about 20-35 degrees", "Tilt target up/down about 20-35 degrees",
                   "Use varied sizes and corner regions; keep target sharp and fully visible"]
        message = "; ".join(latest[3]["reasons"]) if latest and latest[3]["reasons"] else "Target passes capture checks" if latest else "Waiting for image"
        status.configure(text=f"{receiver.status} | views {count}/{board.target_views} | manual lens {profile['profile']['lens_position']:g}\n"
            f"{message}\n{prompts[min(4, count//5)]}")
        if receiver.stop.is_set():
            root.after(500, root.destroy)
        else:
            root.after(40, refresh)

    root.bind("s", save)
    root.bind("S", save)
    root.bind("q", lambda _: close())
    root.protocol("WM_DELETE_WINDOW", close)
    root.after(40, refresh)
    try:
        root.mainloop()
    finally:
        receiver.stop.set()
        received.join(timeout=10)
        detector.join(timeout=5)
        LOG.info("Captured %s real views in %s; calibration fit has not been run", len(session.manifest["views"]), args.dataset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
