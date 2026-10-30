"""MJPEG receiver, Tk viewer, and measured per-frame telemetry."""
from __future__ import annotations
import argparse
import hashlib
import os
import csv
import io
import json
import logging
import queue
import statistics
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

LOG = logging.getLogger("aegis.client")


def read_frame(stream):
    line = stream.readline(4097)
    while line in (b"\r\n", b"\n"):
        line = stream.readline(4097)
    if line != b"--frame\r\n":
        raise ValueError("Missing frame boundary / stream ended")
    headers = {}
    for _ in range(20):
        line = stream.readline(4097)
        if line == b"\r\n":
            break
        if not line or len(line) > 4096:
            raise ValueError("Invalid frame headers")
        key, value = line.decode("ascii").split(":", 1)
        headers[key.lower()] = value.strip()
    else:
        raise ValueError("Too many frame headers")
    length = int(headers["content-length"])
    if not 0 < length <= 8_000_000:
        raise ValueError("Invalid JPEG size")
    data = stream.read(length)
    if len(data) != length or stream.read(2) != b"\r\n":
        raise ValueError("Truncated JPEG")
    return headers, data


def synchronize(base, stop=None):
    samples = []
    for _ in range(5):
        if stop is not None and stop.is_set():
            raise InterruptedError("Clock probe cancelled")
        t0 = time.time_ns()
        with urllib.request.urlopen(base + "/clock", timeout=3) as response:
            remote = json.load(response)
        t3 = time.time_ns()
        t1, t2 = remote["receive_ns"], remote["send_ns"]
        samples.append({"offset_ns": ((t1-t0)+(t2-t3))/2,
                        "rtt_ms": max(0, (t3-t0-(t2-t1))/1e6)})
    result = min(samples, key=lambda sample: sample["rtt_ms"])
    result["uncertainty_ms"] = result["rtt_ms"] / 2
    return result


class Receiver:
    def __init__(self, args, features=None, tracker=None, odometry=None):
        self.args = args
        self.stop = threading.Event()
        self.latest = queue.Queue(maxsize=1)
        self.rows = []
        self.clock_samples = []
        self.errors = 0
        self.connections = 0
        self.display_skips = 0
        self.status = "Connecting"
        self.started = time.monotonic()
        self.clock = None
        self.features = features
        self.feature_latest = ""
        self.tracker = tracker
        self.odometry = odometry
        self.cpu_started = os.times()
        self.last_status_write=0.

    def should_stop(self):
        path=getattr(self.args,'stop_file',None)
        if path and path.exists():self.stop.set()
        return self.stop.is_set()

    def publish_status(self,row):
        path=getattr(self.args,'status_file',None)
        if not path or time.monotonic()-self.last_status_write<.25:return
        payload=dict(written_utc=datetime.now(timezone.utc).isoformat(),connection=self.status,row=row)
        temporary=path.with_suffix('.tmp')
        try:
            temporary.write_text(json.dumps(payload),encoding='utf-8');temporary.replace(path)
        except OSError:
            LOG.warning('Live validation status write skipped; recording continues')
        self.last_status_write=time.monotonic()

    def refresh_clock(self):
        while not self.stop.wait(30):
            try:
                result = synchronize(self.args.url, self.stop)
                self.clock = result
                self.clock_samples.append(result)
            except Exception as exc:
                if not self.stop.is_set():
                    LOG.warning("Clock refresh failed; retaining previous estimate: %s", exc)

    def run(self):
        last_session = None
        last_id = None
        clock_worker = None
        try:
            while not self.should_stop() and time.monotonic()-self.started < self.args.duration:
                try:
                    clock = synchronize(self.args.url, self.stop)
                    self.clock = clock
                    self.clock_samples.append(clock)
                    if clock_worker is None:
                        clock_worker = threading.Thread(target=self.refresh_clock, daemon=True)
                        clock_worker.start()
                    with urllib.request.urlopen(self.args.url + "/stream.mjpg", timeout=3) as stream:
                        self.connections += 1
                        self.status = "LIVE"
                        while not self.should_stop() and time.monotonic()-self.started < self.args.duration:
                            headers, jpeg = read_frame(stream)
                            received_ns = time.time_ns()
                            received_mono = time.monotonic()
                            frame_id = int(headers["x-frame-id"])
                            session = headers["x-session"]
                            gap = max(0, frame_id-last_id-1) if session == last_session and last_id is not None else 0
                            if session == last_session and last_id is not None and frame_id <= last_id:
                                raise ValueError("Non-increasing frame identifier")
                            last_session, last_id = session, frame_id
                            capture_ns = int(headers["x-capture-wall-ns"])
                            decode_start = time.perf_counter()
                            with Image.open(io.BytesIO(jpeg)) as original:
                                image = original.convert("RGB")
                            source_image = image
                            if getattr(self.args,"dashboard",False):
                                self.selected_frame = source_image.copy()
                            decode_ms = (time.perf_counter()-decode_start)*1000
                            clock = self.clock
                            row = {"elapsed_s": received_mono-self.started, "received_wall_ns": received_ns, "received_monotonic_s": received_mono,
                                   "frame_id": frame_id, "session": session, "bytes": len(jpeg),
                                   "sequence_gap": gap, "sensor_ns": int(headers["x-sensor-ns"]),
                                   "estimated_capture_receive_ms": (received_ns+clock["offset_ns"]-capture_ns)/1e6,
                                   "clock_uncertainty_ms": clock["uncertainty_ms"],
                                   "capture_ready_ms": float(headers["x-capture-ready-ms"]),
                                   "decode_ms": decode_ms}
                            row["camera_profile_id"] = headers.get("x-camera-profile-id")
                            row["focus_mode"] = headers.get("x-focus-mode", "unknown")
                            row["lens_position"] = float(headers["x-lens-position"]) if "x-lens-position" in headers else None
                            if self.features is not None:
                                analysis_start = time.perf_counter_ns()
                                image, metrics = self.features.analyze(
                                    image, self.args.features, render=not self.args.headless)
                                row["analysis_ms"] = (time.perf_counter_ns()-analysis_start)/1e6
                                row["gray_ms"] = metrics["gray_ms"]
                                row["detection_order"] = ",".join(metrics["order"])
                                labels = []
                                for method in ("shi-tomasi", "orb"):
                                    if method not in metrics["detectors"]:
                                        continue
                                    values = metrics["detectors"][method]
                                    prefix = method.replace("-", "_")
                                    for key, value in values.items():
                                        row[f"{prefix}_{key}"] = json.dumps(value) if key == "grid_counts" else value
                                    labels.append(f"{method}: {values['count']} points / {values['detect_ms']:.2f} ms / {values['status']}")
                                self.feature_latest = " | ".join(labels)
                                # Stable column order despite alternating detector execution.
                                row = dict(sorted(row.items()))
                            if self.odometry is not None:
                                self.odometry.validate_frame(row, source_image.size)
                            if self.tracker is not None:
                                image, flow = self.tracker.update(source_image, session,
                                    frame_id, row["sensor_ns"], render=not self.args.headless)
                                row.update({f"flow_{key}": value for key, value in flow.items()})
                                success = f"{100*flow['success_ratio']:.1f}%" if flow["success_ratio"] is not None else "N/A"
                                self.feature_latest = (f"LK {flow['status']} | accepted {flow['tracked']}/{flow['attempted']} ({success}) | "
                                    f"active {flow['active']} | new {flow['added']} | {flow['total_ms']:.2f} ms")
                            if self.odometry is not None:
                                pose = self.odometry.update_tracks(self.tracker, flow)
                                row.update({'vo_'+key: json.dumps(value) if isinstance(value,(list,dict)) else value for key,value in pose.items()})
                                self.feature_latest += ' | VO '+pose['status']
                                if not self.args.headless:
                                    image = self.odometry.overlay(image, pose)
                            if getattr(self.args,'record_directory',None):
                                name=f'{session}-{frame_id:08d}.jpg'
                                with (self.args.record_directory/name).open('xb') as recording:
                                    recording.write(jpeg)
                                row['recorded_image']=name
                                row['recorded_sha256']=hashlib.sha256(jpeg).hexdigest()
                            row["pose_ready_monotonic_s"] = time.monotonic()
                            self.publish_status(row)
                            row["processing_ms"] = (time.perf_counter()-decode_start)*1000
                            row["processed_elapsed_s"] = time.monotonic()-self.started
                            self.rows.append(row)
                            if self.args.snapshot and len(self.rows) == 1:
                                self.args.snapshot.parent.mkdir(parents=True, exist_ok=True)
                                source_image.save(self.args.snapshot)
                            if not self.args.headless:
                                if self.latest.full():
                                    try:
                                        self.latest.get_nowait()
                                        self.display_skips += 1
                                    except queue.Empty:
                                        pass
                                self.latest.put_nowait((image, row))
                except Exception as exc:
                    self.errors += 1
                    self.status = "Reconnecting"
                    LOG.warning("Stream interrupted: %s", exc)
                    self.stop.wait(.5)
        finally:
            self.stop.set()
            if clock_worker is not None:
                clock_worker.join(timeout=4)
            self.status = "Stopped"
            self.save()

    def save(self):
        rows = self.rows
        summary = {"frames": len(rows), "connections": self.connections,
                   "completed_utc": datetime.now(timezone.utc).isoformat(),
                   "requested_duration_s": self.args.duration,
                   "receive_span_s": rows[-1]["elapsed_s"]-rows[0]["elapsed_s"] if len(rows)>1 else 0,
                   "connection_errors": self.errors,
                   "sequence_gaps": sum(row["sequence_gap"] for row in rows),
                   "display_queue_skips": self.display_skips,
                   "clock_samples": self.clock_samples,
                   "receive_fps": (len(rows)-1)/(rows[-1]["elapsed_s"]-rows[0]["elapsed_s"]) if len(rows)>1 else 0,
                   "mode": "headless" if self.args.headless else "viewer",
                   "note": "Delay estimates sensor-start to JPEG receipt, excluding display scanout. Sequence gaps count producer frames skipped, not TCP packet loss."}
        if self.odometry is not None:
            from collections import Counter
            summary['odometry'] = {'statuses':dict(Counter(row.get('vo_status','missing') for row in rows)),
                'calibration_profile':self.odometry.calibration['camera_profile']['profile_id'],
                'mean_estimate_ms':statistics.mean(row['vo_estimate_ms'] for row in rows) if rows else None,
                'estimator_version':self.odometry.VERSION,
                'scale_note':'Local maps share arbitrary scale; confirmed recovery reuses that map origin/scale but leaves a path gap. Different map IDs have no scale/origin link. No meters.'}
        if hasattr(self,"dashboard_stats"):
            summary["dashboard"] = self.dashboard_stats
        if getattr(self.args,'record_directory',None):
            if __package__:
                from .validation import resources
            else:
                from validation import resources
            cpu=os.times();wall=max(.001,time.monotonic()-self.started)
            summary['validation_resources'] = resources()
            summary['validation_resources'].update(cpu_seconds=cpu.user+cpu.system-self.cpu_started.user-self.cpu_started.system,
                cpu_percent_one_core=100*(cpu.user+cpu.system-self.cpu_started.user-self.cpu_started.system)/wall,
                logical_processors=os.cpu_count(),wall_s=wall)
            manifest={'experiment':self.args.experiment,'report':str(self.args.report.resolve()),
                'recorded_frames':len(rows),'calibration':str(self.args.odometry.resolve()) if self.args.odometry else None,
                'note':'Raw JPEG recording adds disk/hash overhead to measured receiver processing. No AI upload.'}
            (self.args.record_directory/'manifest.json').write_text(json.dumps(manifest,indent=2))
        for key in ["estimated_capture_receive_ms", "capture_ready_ms", "decode_ms", "processing_ms"]:
            values = sorted(row[key] for row in rows)
            summary[key] = {"mean": statistics.mean(values),
                            "p95": values[min(len(values)-1, int(.95*len(values)))],
                            "min": min(values), "max": max(values)} if values else None
        summary["processing_fps"] = (len(rows)-1)/(rows[-1]["processed_elapsed_s"]-rows[0]["processed_elapsed_s"]) if len(rows)>1 else 0
        if self.tracker is not None:
            from collections import Counter
            tracking = self.tracker.metadata()
            attempted = sum(row["flow_attempted"] for row in rows)
            tracked = sum(row["flow_tracked"] for row in rows)
            tracking.update({"attempted_correspondences": attempted, "accepted_correspondences": tracked,
                "weighted_success_ratio": tracked/attempted if attempted else None,
                "new_features": sum(row["flow_added"] for row in rows),
                "initial_seed_features": sum(row["flow_added"] for row in rows if row["flow_reset_reason"] == "startup"),
                "topup_features": sum(row["flow_added"] for row in rows if not row["flow_reset_reason"]),
                "topup_events": sum(row["flow_replacement_event"] for row in rows if not row["flow_reset_reason"]),
                "replacement_events": sum(row["flow_replacement_event"] for row in rows),
                "status_frames": dict(Counter(row["flow_status"] for row in rows)),
                "reset_reasons": dict(Counter(row["flow_reset_reason"] for row in rows if row["flow_reset_reason"]))})
            for key in ("tracked", "active", "mean_flow_px", "flow_spread_px", "mean_fb_error_px", "flow_ms", "renewal_ms", "total_ms", "coverage"):
                values = sorted(row[f"flow_{key}"] for row in rows if row[f"flow_{key}"] is not None)
                tracking[key] = {"mean": statistics.mean(values), "p95": values[min(len(values)-1,int(.95*len(values)))],
                                 "min": min(values), "max": max(values)} if values else None
            for key in ("forward", "backward", "consistency", "motion", "error"):
                tracking[f"rejected_{key}"] = sum(row[f"flow_rejected_{key}"] for row in rows)
            summary["tracking"] = tracking
        if self.features is not None:
            summary["features"] = self.features.metadata()
            summary["features"]["mode"] = self.args.features
            summary["features"]["detectors"] = {}
            for method in ("shi-tomasi", "orb"):
                prefix = method.replace("-", "_")
                if not rows or f"{prefix}_count" not in rows[0]:
                    continue
                result = {}
                for key in ("count", "detect_ms", "coverage", "occupied_cells"):
                    values = sorted(row[f"{prefix}_{key}"] for row in rows)
                    result[key] = {"mean": statistics.mean(values), "min": min(values),
                                   "max": max(values), "p95": values[min(len(values)-1, int(.95*len(values)))]}
                result["no_feature_frames"] = sum(row[f"{prefix}_count"] == 0 for row in rows)
                result["error_frames"] = sum(row[f"{prefix}_status"] == "error" for row in rows)
                result["warning_frames"] = sum(row[f"{prefix}_status"] != "ok" for row in rows)
                summary["features"]["detectors"][method] = result
            for key in ("analysis_ms", "processing_ms", "gray_ms"):
                values = sorted(row[key] for row in rows)
                summary[key] = {"mean": statistics.mean(values), "p95": values[min(len(values)-1, int(.95*len(values)))]} if values else None
        self.args.report.parent.mkdir(parents=True, exist_ok=True)
        self.args.report.write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
        if rows:
            with self.args.report.with_suffix(".csv").open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        LOG.info("Results: %s", summary)


def show(receiver):
    import tkinter as tk
    from PIL import ImageTk
    root = tk.Tk()
    root.title("AEGIS - Phase 5 visual odometry" if receiver.odometry else
               "AEGIS — Phase 3 optical flow" if receiver.tracker else
               "AEGIS — Phase 2 feature detection" if receiver.features else "AEGIS — Phase 1 live camera")
    root.configure(bg="#101820")
    label = tk.Label(root, bg="#101820")
    label.pack()
    status = tk.Label(root, bg="#101820", fg="#a9e4dd", font=("Consolas", 11))
    status.pack(padx=12, pady=12)

    def close():
        receiver.stop.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)

    def refresh():
        try:
            image, row = receiver.latest.get_nowait()
            if receiver.odometry:
                image = image.copy()
                image.thumbnail((640, 560))
            photo = ImageTk.PhotoImage(image)
            label.configure(image=photo)
            label.image = photo
        except queue.Empty:
            pass
        rows = receiver.rows
        recent = rows[-30:]
        fps = (len(recent)-1)/(recent[-1]["elapsed_s"]-recent[0]["elapsed_s"]) if len(recent)>1 else 0
        latency = recent[-1]["estimated_capture_receive_ms"] if recent else 0
        uncertainty = recent[-1]["clock_uncertainty_ms"] if recent else 0
        status.configure(text=f"{receiver.status} | {fps:.1f} receive FPS | estimated delay {latency:.1f} +/- {uncertainty:.1f} ms\n"
                         f"Frames {len(rows)} | sequence gaps {sum(row['sequence_gap'] for row in rows)} | errors {receiver.errors} | Q / close to stop\n"
                         f"{receiver.feature_latest}")
        if receiver.stop.is_set():
            root.after(500, root.destroy)
        else:
            root.after(20, refresh)

    root.bind("q", lambda _: close())
    root.after(20, refresh)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--duration", type=float, default=3600)
    parser.add_argument("--report", type=Path, default=Path("results/reports/stream.json"))
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--features", choices=["none", "shi-tomasi", "orb", "both"], default="none")
    parser.add_argument("--feature-config", type=Path, default=Path("configs/features.json"))
    parser.add_argument("--tracking", action="store_true")
    parser.add_argument("--tracking-config", type=Path, default=Path("configs/tracking.json"))
    parser.add_argument("--odometry", type=Path, help="Reviewed real calibration JSON; implies tracking")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--record-directory",type=Path)
    parser.add_argument("--experiment",default="unlabeled")
    parser.add_argument('--status-file',type=Path,help='Optional atomic live telemetry for validation guidance')
    parser.add_argument('--stop-file',type=Path,help='Gracefully stop and save when this file appears')
    args = parser.parse_args()
    if args.stop_file and args.stop_file.exists():parser.error('Stop file already exists; choose a new trial path')
    if args.status_file and not args.status_file.parent.is_dir():parser.error('Status directory must exist')
    if args.record_directory:
        args.record_directory.mkdir(parents=True,exist_ok=False)
    if args.dashboard and (not args.odometry or args.headless):
        parser.error("Dashboard requires --odometry and a visible viewer")
    if args.odometry:
        args.tracking = True
    if args.duration <= 0:
        parser.error("duration must be positive")
    if args.report.exists() or args.report.with_suffix(".csv").exists():
        parser.error("Report exists; choose a new report name")
    if args.tracking and args.features != "none":
        parser.error("Choose tracking or detector comparison; tracking seeds its own Shi-Tomasi features")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    features = None
    if args.features != "none":
        if __package__:
            from .feature_detector import DetectorSuite, FeatureConfig
        else:
            from feature_detector import DetectorSuite, FeatureConfig
        features = DetectorSuite(FeatureConfig.load(args.feature_config))
    tracker = None
    if args.tracking:
        if __package__:
            from .optical_flow import OpticalFlowTracker, FlowConfig
        else:
            from optical_flow import OpticalFlowTracker, FlowConfig
        tracker = OpticalFlowTracker(FlowConfig.load(args.tracking_config))
    if args.odometry:
        if __package__:
            from .visual_odometry import VisualOdometry
        else:
            from visual_odometry import VisualOdometry
    odometry = VisualOdometry(json.loads(args.odometry.read_text())) if args.odometry else None
    receiver = Receiver(args, features, tracker, odometry)
    worker = threading.Thread(target=receiver.run, daemon=True)
    worker.start()
    try:
        if args.headless:
            while worker.is_alive():
                worker.join(.5)
        else:
            if args.dashboard:
                if __package__:
                    from .navigation_dashboard import show_dashboard
                else:
                    from navigation_dashboard import show_dashboard
                show_dashboard(receiver)
            else:
                show(receiver)
    except KeyboardInterrupt:
        receiver.stop.set()
    finally:
        receiver.stop.set()
        worker.join(10)
    return 0 if receiver.rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
