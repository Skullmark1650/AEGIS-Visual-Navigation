"""Synthetic calibration verification. This never creates a real-camera calibration."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from .camera_calibration import BoardConfig, object_points, corner_distance, calibrate_points


def synthetic_observations(count=30, seed=12):
    rng = np.random.default_rng(seed)
    board = BoardConfig()
    matrix = np.float64([[530, 0, 320], [0, 525, 240], [0, 0, 1]])
    distortion = np.float64([-.14, .04, .001, -.002, .005])
    objects = object_points(board, 20)
    observations = []
    for _ in range(10000):
        rotation = rng.uniform([-.6, -.6, -.3], [.6, .6, .3])
        translation = np.float64([rng.uniform(-230, 80), rng.uniform(-160, 50), rng.uniform(430, 850)])
        projected, _ = cv2.projectPoints(objects, rotation, translation, matrix, distortion)
        points = projected.reshape(-1, 2)
        if not ((points[:, 0] > 25).all() and (points[:, 0] < 615).all() and
                (points[:, 1] > 25).all() and (points[:, 1] < 455).all()):
            continue
        if any(corner_distance(points, other) < 15 for other in observations):
            continue
        observations.append((points+rng.normal(0, .03, points.shape)).astype(np.float32))
        if len(observations) == count:
            return board, matrix, distortion, observations
    raise RuntimeError("Could not produce the requested diverse synthetic observations")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists(): parser.error("Report already exists")
    board, truth_matrix, truth_distortion, observations = synthetic_observations()
    result = calibrate_points(observations, (640, 480), board, 20, source_kind="synthetic", profile=None)
    maximum_error = float(np.abs(np.asarray(result["camera_matrix"])-truth_matrix).max())
    report = {"source_kind": "synthetic", "note": "Projected point data with 0.03-pixel per-axis Gaussian noise. Not IMX708 calibration or measured optical accuracy.",
        "ground_truth_camera_matrix": truth_matrix.tolist(), "ground_truth_distortion": truth_distortion.tolist(),
        "maximum_intrinsic_matrix_error_px": maximum_error,
        "passed": result["numerical_checks_passed"] and maximum_error < 3 and result["heldout_mean_rms_px"] < .2,
        "fit": result}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("source_kind", "maximum_intrinsic_matrix_error_px", "passed")}, indent=2))
    print("Synthetic training / heldout RMS:", result["training_rms_px"], result["heldout_mean_rms_px"])
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
