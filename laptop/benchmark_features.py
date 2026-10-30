"""Repeatable paired offline detector benchmark; altered images are synthetic."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import time
import cv2
import numpy as np
from PIL import Image
from .feature_detector import DetectorSuite, FeatureConfig, METHODS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/features.json"))
    parser.add_argument("--repeats", type=int, default=100)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--overlays", type=Path, required=True)
    args = parser.parse_args()
    if args.repeats < 10:
        parser.error("At least 10 repetitions required")
    if args.report.exists() or args.report.with_suffix(".csv").exists() or args.overlays.exists():
        parser.error("Choose fresh report and overlay paths")
    suite = DetectorSuite(FeatureConfig.load(args.config))
    with Image.open(args.image) as image:
        rgb = np.asarray(image.convert("RGB"))
    cases = {"real_frame": rgb,
             "synthetic_dark_20_percent": (rgb.astype(np.float32)*.2).astype(np.uint8),
             "synthetic_blur_21px": cv2.GaussianBlur(rgb, (21, 21), 0),
             "synthetic_uniform_gray": np.full_like(rgb, 128)}
    args.overlays.mkdir(parents=True)
    rows = []
    results = {}
    for name, image in cases.items():
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        for _ in range(5):
            for method in METHODS:
                suite.detect(gray, method)
        for repeat in range(args.repeats):
            order = METHODS if repeat % 2 == 0 else METHODS[::-1]
            for method in order:
                _, metrics = suite.detect(gray, method)
                rows.append({"case": name, "repeat": repeat, "method": method,
                             "order": ",".join(order), **metrics})
        output, _ = suite.analyze(image, render=True)
        output.save(args.overlays / f"{name}.jpg")
        results[name] = {}
        for method in METHODS:
            selected = [row for row in rows if row["case"] == name and row["method"] == method]
            timings = sorted(row["detect_ms"] for row in selected)
            results[name][method] = {
                "count": selected[0]["count"], "coverage": selected[0]["coverage"],
                "grid_counts": selected[0]["grid_counts"], "status": selected[0]["status"],
                "mean_ms": statistics.mean(timings), "median_ms": statistics.median(timings),
                "p95_ms": timings[min(len(timings)-1, int(.95*len(timings)))],
                "error_calls": sum(row["status"] == "error" for row in selected)}
    report = {"source_image": str(args.image), "source_sha256": hashlib.sha256(args.image.read_bytes()).hexdigest(),
              "repetitions_per_case_per_detector": args.repeats, "warmup_calls_per_case_per_detector": 5,
              "image_size": list(rgb.shape[:2][::-1]), "suite": suite.metadata(), "cases": results,
              "note": "Repeated fixed frames measure runtime, not independent scene samples. Dark/blur/uniform cases are synthetic; no physical lighting claims."}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    with args.report.with_suffix(".csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
