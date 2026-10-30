"""Known image-plane motion and texture-loss tests; all sequences are synthetic."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import cv2
import numpy as np
from PIL import Image
from .optical_flow import FlowConfig, OpticalFlowTracker


def mean_available(rows, key):
    values = [row[key] for row in rows if row[key] is not None]
    return statistics.mean(values) if values else None


def cases(rgb, length=20):
    height, width = rgb.shape[:2]
    identity = np.eye(3, dtype=np.float64)
    for name in ("stationary", "horizontal_2px", "vertical_2px", "rotation_0.4deg",
                 "rapid_horizontal_15px", "partial_occlusion", "full_texture_loss", "time_gap"):
        sequence = []
        for index in range(length):
            transform = identity.copy()
            if name == "horizontal_2px": transform[0, 2] = 2*index
            if name == "vertical_2px": transform[1, 2] = 2*index
            if name == "rapid_horizontal_15px": transform[0, 2] = 15*index
            if name == "rotation_0.4deg":
                transform[:2] = cv2.getRotationMatrix2D((width/2, height/2), .4*index, 1)
            frame = cv2.warpAffine(rgb, transform[:2], (width, height))
            if name == "partial_occlusion" and 5 <= index < 10:
                frame[:, :3*width//4] = 128
            if name == "full_texture_loss" and 5 <= index < 10:
                frame[:] = 128
            frame_id = index+1+(10 if name == "time_gap" and index >= 10 else 0)
            sequence.append((frame, transform, frame_id, frame_id*66_666_667))
        yield name, sequence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/tracking.json"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--overlays", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists() or args.report.with_suffix(".csv").exists() or args.overlays.exists():
        parser.error("Choose unused report and overlay paths")
    with Image.open(args.image) as image:
        rgb = np.asarray(image.convert("RGB"))
    config = FlowConfig.load(args.config)
    args.overlays.mkdir(parents=True)
    rows = []
    report = {"source": str(args.image), "source_sha256": hashlib.sha256(args.image.read_bytes()).hexdigest(),
        "note": "Synthetic transformations of one real image. Pixel ground truth, not measured camera motion or navigation accuracy.",
        "suite": OpticalFlowTracker(config).metadata(), "cases": {}}
    for name, sequence in cases(rgb):
        tracker = OpticalFlowTracker(config)
        errors = []
        previous_transform = None
        local_rows = []
        for index, (frame, transform, frame_id, sensor_ns) in enumerate(sequence):
            output, metrics = tracker.update(frame, name, frame_id, sensor_ns, render=True)
            epe = None
            if name in ("stationary", "horizontal_2px", "vertical_2px", "rotation_0.4deg", "rapid_horizontal_15px") and len(tracker.last_current):
                relative = transform @ np.linalg.inv(previous_transform)
                old_homogeneous = np.column_stack([tracker.last_previous, np.ones(len(tracker.last_previous))])
                expected = (relative @ old_homogeneous.T).T[:, :2]
                error = np.linalg.norm(tracker.last_current-expected, axis=1)
                errors.extend(error.tolist())
                epe = float(np.median(error))
            previous_transform = transform
            row = {"case": name, "index": index, "median_endpoint_error_px": epe, **metrics}
            local_rows.append(row)
            rows.append(row)
            if index in (5, 10, 11):
                output.save(args.overlays/f"{name}-{index:02d}.jpg")
        attempted = sum(row["attempted"] for row in local_rows)
        accepted = sum(row["tracked"] for row in local_rows)
        values = [row["total_ms"] for row in local_rows]
        entry = {"frames": len(local_rows), "attempted": attempted, "accepted": accepted,
            "weighted_success_ratio": accepted/attempted if attempted else None,
            "median_endpoint_error_px": float(np.median(errors)) if errors else None,
            "p95_endpoint_error_px": float(np.percentile(errors, 95)) if errors else None,
            "mean_processing_ms": statistics.mean(values),
            "features_added": sum(row["added"] for row in local_rows),
            "replacement_events": sum(row["replacement_event"] for row in local_rows),
            "reset_reasons": [row["reset_reason"] for row in local_rows if row["reset_reason"]],
            "texture_return_frame10_added": local_rows[10]["added"],
            "frame11_tracked": local_rows[11]["tracked"],
            "frame5_tracked": local_rows[5]["tracked"],
            "mean_flow_spread_px": mean_available(local_rows, "flow_spread_px"),
            "mean_median_dx_px": mean_available(local_rows, "median_dx_px"),
            "mean_median_dy_px": mean_available(local_rows, "median_dy_px"),
            "mean_flow_px": mean_available(local_rows, "mean_flow_px")}
        if name in ("stationary", "horizontal_2px", "vertical_2px", "rotation_0.4deg"):
            entry["passed"] = bool(errors) and entry["median_endpoint_error_px"] < 1 and accepted >= 100
        elif name == "full_texture_loss":
            entry["passed"] = local_rows[5]["tracked"] == 0 and local_rows[10]["added"] > 0 and local_rows[10]["tracked"] == 0 and local_rows[11]["tracked"] > 0
        elif name == "partial_occlusion":
            entry["passed"] = any(row["added"] > 0 for row in local_rows[5:]) and local_rows[11]["tracked"] > 0
        elif name == "time_gap":
            entry["passed"] = local_rows[10]["reset_reason"] == "frame_gap" and local_rows[10]["tracked"] == 0 and local_rows[11]["tracked"] > 0
        else:
            entry["passed"] = None  # Rapid motion is an exploratory failure-envelope test.
        report["cases"][name] = entry
    report["passed"] = all(entry["passed"] is not False for entry in report["cases"].values())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    with args.report.with_suffix(".csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
