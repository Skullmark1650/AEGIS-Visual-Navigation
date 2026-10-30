"""Latest-frame MJPEG server, accessed through an SSH forward."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import logging
import math
import os
import signal
import socket
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = logging.getLogger("aegis.server")


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    for key, low, high in [("width", 64, 1920), ("height", 64, 1080),
                           ("fps", 1, 30), ("jpeg_quality", 10, 95),
                           ("port", 1024, 65535)]:
        if type(config.get(key)) is not int or not low <= config[key] <= high:
            raise ValueError(f"{key} must be an integer between {low} and {high}")
    if config.get("host") != "127.0.0.1":
        raise ValueError("Use loopback with SSH forwarding for this prototype")
    position = config.get("lens_position")
    if config.get("focus_mode") != "manual" or isinstance(position, bool) or not isinstance(position, (int, float)) or not math.isfinite(position) or not 0 <= position <= 32:
        raise ValueError("Explicit manual focus and lens_position in 0..32 required")
    return config


class Frames:
    def __init__(self):
        self.condition = threading.Condition()
        self.frame = None
        self.stop = threading.Event()
        self.error = None
        self.session = str(uuid.uuid4())
        self.profile = None

    def capture(self, config):
        camera = None
        try:
            from picamera2 import Picamera2
            from libcamera import controls
            camera = Picamera2()
            lens_range = camera.camera_controls["LensPosition"]
            if not lens_range[0] <= config["lens_position"] <= lens_range[1]:
                raise ValueError("Requested lens position outside this camera's advertised range")
            duration = round(1_000_000 / config["fps"])
            camera.configure(camera.create_video_configuration(
                main={"size": (config["width"], config["height"]), "format": "BGR888"},
                controls={"FrameDurationLimits": (duration, duration),
                          "AfMode": controls.AfModeEnum.Manual,
                          "LensPosition": float(config["lens_position"])}, buffer_count=4))
            camera.start(show_preview=False)
            configured = camera.camera_configuration()
            settle_started = time.monotonic()
            sequence = 0
            while not self.stop.is_set():
                request = camera.capture_request()
                try:
                    metadata = request.get_metadata()
                    actual_lens = float(metadata.get("LensPosition", float("nan")))
                    if not math.isfinite(actual_lens) or abs(actual_lens-config["lens_position"]) > .05:
                        if time.monotonic()-settle_started > 3:
                            raise RuntimeError("Camera did not confirm the requested manual lens position")
                        continue
                    profile = {"camera_model": camera.camera_properties.get("Model", "unknown"),
                        "camera_id": Picamera2.global_camera_info()[0]["Id"],
                        "image_size": list(configured["main"]["size"]),
                        "main_format": str(configured["main"]["format"]),
                        "raw_size": list(configured["raw"]["size"]),
                        "raw_format": str(configured["raw"]["format"]),
                        "transform": str(configured["transform"]),
                        "scaler_crop": list(metadata["ScalerCrop"]),
                        "focus_mode": "manual", "lens_position": float(config["lens_position"])}
                    profile_id = hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()
                    image = request.make_image("main")
                    sensor_ns = int(metadata["SensorTimestamp"])
                    # libcamera sensor timestamps use Linux CLOCK_BOOTTIME.
                    capture_ns = time.time_ns() - (
                        time.clock_gettime_ns(time.CLOCK_BOOTTIME) - sensor_ns)
                    encoded = io.BytesIO()
                    image.save(encoded, format="JPEG", quality=config["jpeg_quality"])
                    jpeg = encoded.getvalue()
                finally:
                    request.release()
                ready_ms = (time.time_ns() - capture_ns) / 1e6
                sequence += 1
                with self.condition:
                    self.profile = {"profile_id": profile_id, "profile": profile,
                                    "producer_session": self.session, "observed_lens_position": actual_lens}
                    self.frame = (sequence, jpeg, sensor_ns, capture_ns, ready_ms, profile_id, actual_lens)
                    self.condition.notify_all()
        except Exception as exc:
            LOG.exception("Camera producer failed")
            self.error = str(exc)
            self.stop.set()
        finally:
            if camera is not None:
                camera.close()
            with self.condition:
                self.condition.notify_all()


def handler_for(frames):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            LOG.info(fmt, *args)

        def do_GET(self):
            self.connection.settimeout(5)
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if self.path == "/clock":
                received_ns = time.time_ns()
                payload = json.dumps({"receive_ns": received_ns,
                                      "send_ns": time.time_ns()}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if self.path == "/profile":
                with frames.condition:
                    profile = frames.profile
                payload = json.dumps(profile or {"status": "camera not ready"}).encode()
                self.send_response(200 if profile else 503)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if self.path != "/stream.mjpg":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            last = -1
            try:
                while not frames.stop.is_set():
                    with frames.condition:
                        frames.condition.wait_for(
                            lambda: frames.stop.is_set() or
                            (frames.frame is not None and frames.frame[0] != last), timeout=5)
                        if frames.stop.is_set():
                            break
                        frame = frames.frame
                    if frame is None or frame[0] == last:
                        continue
                    last, jpeg, sensor_ns, capture_ns, ready_ms, profile_id, actual_lens = frame
                    headers = (
                        f"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n"
                        f"X-Session: {frames.session}\r\nX-Frame-Id: {last}\r\n"
                        f"X-Sensor-Ns: {sensor_ns}\r\nX-Capture-Wall-Ns: {capture_ns}\r\n"
                        f"X-Capture-Ready-Ms: {ready_ms:.3f}\r\n"
                        f"X-Camera-Profile-Id: {profile_id}\r\nX-Focus-Mode: manual\r\n"
                        f"X-Lens-Position: {actual_lens:.6f}\r\n\r\n").encode()
                    self.wfile.write(headers + jpeg + b"\r\n")
                    self.wfile.flush()
            except (OSError, TimeoutError):
                LOG.info("Stream client disconnected")
            self.close_connection = True
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/stream.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(args.config)
    frames = Frames()
    server = ThreadingHTTPServer((config["host"], config["port"]), handler_for(frames))
    server.daemon_threads = True
    server.timeout = .5
    pid_path = Path("results/server.pid")
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(os.getpid()), encoding="ascii")

    def shutdown(*_):
        frames.stop.set()
        with frames.condition:
            frames.condition.notify_all()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGHUP, shutdown)
    worker = threading.Thread(target=frames.capture, args=(config,), daemon=True)
    worker.start()
    LOG.info("Listening on %s:%s config=%s", config["host"], config["port"], config)
    try:
        while not frames.stop.is_set():
            server.handle_request()
    finally:
        shutdown()
        server.server_close()
        worker.join(timeout=10)
        if pid_path.exists() and pid_path.read_text().strip() == str(os.getpid()):
            pid_path.unlink()
    return 1 if frames.error else 0


if __name__ == "__main__":
    raise SystemExit(main())
