"""Checkerboard calibration, profile compatibility, and explicit undistortion preview."""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class BoardConfig:
    columns: int = 9
    rows: int = 6
    nominal_square_mm: float = 20
    target_views: int = 25
    minimum_views: int = 20
    minimum_board_area: float = .04
    minimum_border_px: int = 8
    minimum_spacing_px: int = 8
    minimum_sharpness: float = 40
    duplicate_rms_px: float = 12
    maximum_rms_px: float = 1
    maximum_view_rms_px: float = 1.5

    def __post_init__(self):
        for key, low, high in [("columns", 3, 20), ("rows", 3, 20),
            ("target_views", 20, 100), ("minimum_views", 20, 100),
            ("minimum_border_px", 1, 100), ("minimum_spacing_px", 2, 100)]:
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"Invalid {key}")
        for key in ("nominal_square_mm", "minimum_board_area", "minimum_sharpness", "duplicate_rms_px", "maximum_rms_px", "maximum_view_rms_px"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid {key}")
        if self.minimum_board_area >= 1 or self.target_views < self.minimum_views:
            raise ValueError("Invalid area or view counts")

    @classmethod
    def load(cls, path):
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


def object_points(board, square_mm):
    if not math.isfinite(square_mm) or square_mm <= 0:
        raise ValueError("Measured square size must be positive and finite")
    points = np.zeros((board.rows*board.columns, 3), np.float32)
    points[:, :2] = np.mgrid[0:board.columns, 0:board.rows].T.reshape(-1, 2)*square_mm
    return points


def geometry(corners, size, board):
    points = corners.reshape(board.rows, board.columns, 2)
    height, width = size[1], size[0]
    hull = cv2.convexHull(corners.astype(np.float32))
    top = np.linalg.norm(points[0, -1]-points[0, 0])
    bottom = np.linalg.norm(points[-1, -1]-points[-1, 0])
    left = np.linalg.norm(points[-1, 0]-points[0, 0])
    right = np.linalg.norm(points[-1, -1]-points[0, -1])
    return {"center": corners.reshape(-1, 2).mean(axis=0).tolist(),
        "area_fraction": float(cv2.contourArea(hull)/(width*height)),
        "opposite_edge_ratio": float(max(top/max(bottom, .001), bottom/max(top, .001), left/max(right, .001), right/max(left, .001))),
        "minimum_spacing_px": float(min(np.linalg.norm(np.diff(points, axis=1), axis=2).min(), np.linalg.norm(np.diff(points, axis=0), axis=2).min()))}


def inspect_board(image, board):
    """Subpixel SB corner detection, then heuristic capture-quality checks."""
    rgb = np.asarray(image)
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("Expected uint8 RGB image")
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    found, corners = cv2.findChessboardCornersSB(gray, (board.columns, board.rows),
        flags=cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_EXHAUSTIVE)
    if not found:
        return None, {"found": False, "accepted": False, "reasons": ["Complete checkerboard not detected"]}
    corners = corners.reshape(-1, 2).astype(np.float32)
    size = (gray.shape[1], gray.shape[0])
    info = geometry(corners, size, board)
    # Estimate the board's outer boundary from the internal-corner grid.
    grid = object_points(board, 1)[:, :2]
    homography, _ = cv2.findHomography(grid, corners, 0)
    outer = np.float32([[-1, -1], [board.columns, -1], [board.columns, board.rows], [-1, board.rows]])
    projected = cv2.perspectiveTransform(outer.reshape(1, -1, 2), homography).reshape(-1, 2)
    margin = min(float(projected[:, 0].min()), float(projected[:, 1].min()),
                 size[0]-1-float(projected[:, 0].max()), size[1]-1-float(projected[:, 1].max()))
    x0, y0 = np.floor(corners.min(axis=0)).astype(int)
    x1, y1 = np.ceil(corners.max(axis=0)).astype(int)
    roi = gray[max(0, y0):min(size[1], y1+1), max(0, x0):min(size[0], x1+1)]
    sharpness = float(cv2.Laplacian(roi, cv2.CV_64F).var())
    reasons = []
    if info["area_fraction"] < board.minimum_board_area: reasons.append("Target too small")
    if margin < board.minimum_border_px: reasons.append("Keep full target and white margin inside image")
    if info["minimum_spacing_px"] < board.minimum_spacing_px: reasons.append("Squares too small in image")
    if sharpness < board.minimum_sharpness: reasons.append("Target appears blurred; hold still/check focus")
    info.update(found=True, accepted=not reasons, reasons=reasons, sharpness=sharpness, outer_margin_px=margin)
    return corners, info


def corner_distance(first, second):
    a, b = np.asarray(first).reshape(-1, 2), np.asarray(second).reshape(-1, 2)
    return min(float(np.sqrt(np.mean(np.sum((a-b)**2, axis=1)))),
               float(np.sqrt(np.mean(np.sum((a-b[::-1])**2, axis=1)))))


def verify_profile(profile):
    content = profile["profile"]
    required = {"camera_id", "camera_model", "image_size", "scaler_crop", "focus_mode", "lens_position", "main_format", "raw_size", "raw_format", "transform"}
    if not required.issubset(content) or not content["camera_id"] or content["camera_model"] == "unknown":
        raise ValueError("Incomplete camera geometry profile")
    expected = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    if expected != profile["profile_id"] or content["focus_mode"] != "manual":
        raise ValueError("Camera profile is inconsistent or focus is not manual")
    position = content["lens_position"]
    if isinstance(position, bool) or not isinstance(position, (int, float)) or not math.isfinite(position):
        raise ValueError("Missing finite manual lens position")
    return content


def calibrate_points(observations, size, board, square_mm, *, source_kind, profile):
    """Fit intrinsics on 4/5 views and evaluate held-out views after pose fitting."""
    if source_kind not in {"real_camera", "synthetic"}:
        raise ValueError("Explicit real_camera or synthetic provenance required")
    if source_kind == "real_camera":
        content = verify_profile(profile)
        if list(size) != content["image_size"]:
            raise ValueError("Image size and camera profile disagree")
    if len(observations) < board.minimum_views:
        raise ValueError(f"Need at least {board.minimum_views} distinct usable views")
    points = [np.asarray(item, np.float32).reshape(-1, 2) for item in observations]
    for index, item in enumerate(points):
        if item.shape != (board.rows*board.columns, 2) or not np.isfinite(item).all():
            raise ValueError("Invalid observed corner array")
        if any(corner_distance(item, other) < board.duplicate_rms_px for other in points[:index]):
            raise ValueError("Near-duplicate views; move/tilt target more between captures")
    shapes = [geometry(item, size, board) for item in points]
    centers = {(min(2, int(info["center"][0]*3/size[0])), min(2, int(info["center"][1]*3/size[1]))) for info in shapes}
    scale_ratio = math.sqrt(max(info["area_fraction"] for info in shapes)/min(info["area_fraction"] for info in shapes))
    if len(centers) < 3 or scale_ratio < 1.3 or max(info["opposite_edge_ratio"] for info in shapes) < 1.1:
        raise ValueError("Insufficient diversity: use at least three image regions, varied sizes, and perspective tilts")
    objects = object_points(board, square_mm)
    train = [index for index in range(len(points)) if index % 5 != 0]
    holdout = [index for index in range(len(points)) if index % 5 == 0]
    result = cv2.calibrateCameraExtended([objects.copy() for _ in train], [points[i] for i in train],
        tuple(size), None, None, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-9))
    rms, matrix, distortion, rotations, translations, std_intrinsics, _, _ = result
    if not np.isfinite(matrix).all() or not np.isfinite(distortion).all() or not math.isfinite(rms):
        raise ValueError("Nonfinite calibration fit")
    per_view = []
    normals = []
    for index, observed in enumerate(points):
        if index in train:
            at = train.index(index)
            rotation, translation = rotations[at], translations[at]
        else:
            ok, rotation, translation = cv2.solvePnP(objects, observed, matrix, distortion)
            if not ok: raise ValueError("Held-out pose fit failed")
        projected, _ = cv2.projectPoints(objects, rotation, translation, matrix, distortion)
        error = float(np.sqrt(np.mean(np.sum((projected.reshape(-1, 2)-observed)**2, axis=1))))
        normal = cv2.Rodrigues(rotation)[0][:, 2]
        normals.append(normal)
        per_view.append({"index": index, "split": "train" if index in train else "holdout",
            "rms_px": error, "rotation_board_to_camera": rotation.ravel().tolist(),
            "translation_board_to_camera_mm": translation.ravel().tolist()})
    heldout = [item["rms_px"] for item in per_view if item["split"] == "holdout"]
    normals = np.asarray(normals)
    tilt = np.degrees(np.arccos(np.clip(np.abs(normals[:, 2]), 0, 1)))
    warnings = []
    if rms > board.maximum_rms_px: warnings.append("Training RMS exceeds threshold")
    if max(item["rms_px"] for item in per_view) > board.maximum_view_rms_px: warnings.append("At least one view has high reprojection RMS")
    if np.mean(heldout) > board.maximum_rms_px: warnings.append("Held-out RMS exceeds threshold")
    if max(tilt) < 15 or np.ptp(normals[:, 0]) < .12 or np.ptp(normals[:, 1]) < .12:
        warnings.append("Fitted target normals need more tilt diversity in both axes")
    if matrix[0, 0] <= 0 or matrix[1, 1] <= 0 or not 0 <= matrix[0, 2] < size[0] or not 0 <= matrix[1, 2] < size[1]:
        warnings.append("Intrinsics are implausible; review dataset and board geometry")
    return {"kind": "aegis_camera_calibration", "source_kind": source_kind,
        "created_utc": datetime.now(timezone.utc).isoformat(), "image_size": list(size),
        "camera_profile": profile, "board": asdict(board), "supplied_square_mm": square_mm,
        "model": "opencv_pinhole_5", "camera_matrix": matrix.tolist(), "distortion": distortion.ravel().tolist(),
        "training_rms_px": float(rms), "heldout_mean_rms_px": float(np.mean(heldout)),
        "per_view": per_view, "linearized_intrinsic_stddev": std_intrinsics.ravel().tolist(),
        "diversity": {"center_cells_of_9": len(centers), "size_ratio": scale_ratio, "maximum_fitted_tilt_deg": float(max(tilt))},
        "numerical_checks_passed": not warnings, "requires_visual_review": True, "warnings": warnings,
        "opencv": cv2.__version__, "note": "Reprojection residuals are fit/generalization diagnostics, not navigation accuracy. Held-out poses are fitted with fixed intrinsics; square size is user-supplied."}


def undistort_rgb(image, calibration, profile, *, allow_synthetic=False, allow_candidate=False):
    if calibration.get("source_kind") not in {"real_camera", "synthetic"}:
        raise ValueError("Missing calibration provenance")
    if calibration["source_kind"] == "synthetic" and not allow_synthetic:
        raise ValueError("Synthetic calibration is prohibited for camera images")
    if (not calibration["numerical_checks_passed"] or calibration.get("requires_visual_review", True)) and not allow_candidate:
        raise ValueError("Calibration candidate requires explicit review/preview")
    if calibration["source_kind"] == "real_camera":
        verify_profile(profile)
        verify_profile(calibration["camera_profile"])
    if profile != calibration["camera_profile"]:
        # Producer sessions may change; compare stable geometry IDs instead.
        if not profile or not calibration["camera_profile"] or profile["profile_id"] != calibration["camera_profile"]["profile_id"]:
            raise ValueError("Calibration camera/focus/crop profile mismatch")
    array = np.asarray(image)
    if list(array.shape[1::-1]) != calibration["image_size"]:
        raise ValueError("Calibration resolution mismatch")
    matrix = np.asarray(calibration["camera_matrix"], np.float64)
    return cv2.undistort(array, matrix, np.asarray(calibration["distortion"], np.float64), None, matrix)


def fit_dataset(dataset, output, square_mm):
    manifest = json.loads((dataset/"dataset.json").read_text(encoding="utf-8"))
    board = BoardConfig(**manifest["board"])
    profile = manifest["camera_profile"]
    verify_profile(profile)
    observations = []
    sources = []
    for item in manifest["views"]:
        path = dataset/item["file"]
        if path.resolve().parent != dataset.resolve():
            raise ValueError("Invalid dataset image path")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]: raise ValueError("Captured image hash mismatch")
        if item["camera_profile_id"] != profile["profile_id"] or item["focus_mode"] != "manual" or abs(item["lens_position"]-profile["profile"]["lens_position"]) > .05:
            raise ValueError("Mixed camera/focus settings in dataset")
        with Image.open(path) as image:
            if list(image.size) != profile["profile"]["image_size"]: raise ValueError("Mixed image resolutions")
            corners, quality = inspect_board(image.convert("RGB"), board)
        if corners is None or not quality["accepted"]:
            raise ValueError(f"Saved view no longer passes detection/quality: {path.name}")
        observations.append(corners)
        sources.append({"file": item["file"], "sha256": digest})
    result = calibrate_points(observations, profile["profile"]["image_size"], board, square_mm,
                              source_kind="real_camera", profile=profile)
    result["source_images"] = sources
    output.parent.mkdir(parents=True, exist_ok=True)
    result_text = json.dumps(result, indent=2, allow_nan=False)+"\n"
    with output.open("x", encoding="utf-8") as file:
        file.write(result_text)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    fit = sub.add_parser("fit")
    fit.add_argument("--dataset", type=Path, required=True)
    fit.add_argument("--output", type=Path, required=True)
    fit.add_argument("--square-mm", type=float, required=True, help="Measured printed square side, not assumed printer scale")
    preview = sub.add_parser("preview")
    preview.add_argument("--dataset", type=Path, required=True)
    preview.add_argument("--calibration", type=Path, required=True)
    preview.add_argument("--view", default="view-0001.png")
    preview.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "fit":
        result = fit_dataset(args.dataset, args.output, args.square_mm)
        print(json.dumps({key: result[key] for key in ("training_rms_px", "heldout_mean_rms_px", "numerical_checks_passed", "warnings")}, indent=2))
        return 0 if result["numerical_checks_passed"] else 1
    calibration = json.loads(args.calibration.read_text())
    manifest = json.loads((args.dataset/"dataset.json").read_text())
    if args.output.exists() or Path(args.view).name != args.view:
        parser.error("Choose unused output and a dataset image basename")
    with Image.open(args.dataset/args.view) as image:
        rgb = np.asarray(image.convert("RGB"))
    corrected = undistort_rgb(rgb, calibration, manifest["camera_profile"], allow_candidate=True)
    joined = np.concatenate([rgb, corrected], axis=1)
    cv2.putText(joined, "Raw | Undistorted candidate - visual review required", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 170, 0), 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(joined).save(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
