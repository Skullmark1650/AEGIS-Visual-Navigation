"""Independent per-image Shi-Tomasi/ORB detection; no feature tracking."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json
import logging
import math
from pathlib import Path
import time
import cv2
import numpy as np
from PIL import Image

LOG = logging.getLogger("aegis.features")
METHODS = ("shi-tomasi", "orb")


@dataclass(frozen=True)
class FeatureConfig:
    max_features: int = 500
    shi_quality_level: float = 0.01
    shi_min_distance: float = 10
    shi_block_size: int = 7
    orb_scale_factor: float = 1.2
    orb_levels: int = 8
    orb_fast_threshold: int = 20
    orb_edge_threshold: int = 31
    orb_patch_size: int = 31
    grid_columns: int = 4
    grid_rows: int = 3
    minimum_features: int = 30
    minimum_coverage: float = 0.25
    opencv_threads: int = 1

    def __post_init__(self):
        limits = {"max_features": (1, 5000), "shi_block_size": (3, 31),
                  "orb_levels": (1, 16), "orb_fast_threshold": (1, 255),
                  "orb_edge_threshold": (1, 128), "orb_patch_size": (3, 127),
                  "grid_columns": (1, 16), "grid_rows": (1, 16),
                  "minimum_features": (1, 5000), "opencv_threads": (1, 16)}
        for key, (low, high) in limits.items():
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{key} must be integer {low}..{high}")
        for key, low, high in [("shi_quality_level", 0, 1),
                               ("shi_min_distance", 0, 1000),
                               ("orb_scale_factor", 1, 2),
                               ("minimum_coverage", 0, 1)]:
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low < value <= high:
                raise ValueError(f"Invalid {key}")
        if self.shi_block_size % 2 == 0 or self.orb_patch_size % 2 == 0:
            raise ValueError("Corner block and ORB patch sizes must be odd")
        if self.minimum_features > self.max_features:
            raise ValueError("minimum_features cannot exceed max_features")

    @classmethod
    def load(cls, path):
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


def distribution(points: np.ndarray, shape, columns=4, rows=3) -> dict:
    """Row-major grid counts and fraction of cells with at least one detection."""
    height, width = shape[:2]
    counts = np.zeros((rows, columns), dtype=int)
    if len(points):
        x = np.clip((points[:, 0] * columns / width).astype(int), 0, columns-1)
        y = np.clip((points[:, 1] * rows / height).astype(int), 0, rows-1)
        np.add.at(counts, (y, x), 1)
    return {"grid_counts": counts.ravel().tolist(),
            "occupied_cells": int(np.count_nonzero(counts)),
            "coverage": float(np.count_nonzero(counts) / counts.size)}


class DetectorSuite:
    def __init__(self, config: FeatureConfig):
        self.config = config
        cv2.setNumThreads(config.opencv_threads)
        self.orb = cv2.ORB_create(nfeatures=config.max_features,
            scaleFactor=config.orb_scale_factor, nlevels=config.orb_levels,
            fastThreshold=config.orb_fast_threshold,
            edgeThreshold=config.orb_edge_threshold, patchSize=config.orb_patch_size)
        self.calls = 0

    def detect(self, gray: np.ndarray, method: str):
        if method not in METHODS:
            raise ValueError("Unknown detector")
        if not isinstance(gray, np.ndarray) or gray.dtype != np.uint8 or gray.ndim != 2 or not gray.size:
            raise ValueError("Detector input must be a nonempty uint8 grayscale image")
        config = self.config
        started = time.perf_counter_ns()
        error = ""
        try:
            if method == "shi-tomasi":
                corners = cv2.goodFeaturesToTrack(gray, maxCorners=config.max_features,
                    qualityLevel=config.shi_quality_level, minDistance=config.shi_min_distance,
                    blockSize=config.shi_block_size, useHarrisDetector=False)
                points = corners.reshape(-1, 2) if corners is not None else np.empty((0, 2), np.float32)
            else:
                keypoints = self.orb.detect(gray, None)  # Detection only, no BRIEF descriptors.
                points = np.asarray([point.pt for point in keypoints], dtype=np.float32).reshape(-1, 2)
        except cv2.error as exc:
            error = str(exc)
            LOG.exception("%s detector failed", method)
            points = np.empty((0, 2), np.float32)
        elapsed_ms = (time.perf_counter_ns()-started)/1e6
        metrics = {"count": len(points), "detect_ms": elapsed_ms,
                   **distribution(points, gray.shape, config.grid_columns, config.grid_rows)}
        metrics["status"] = ("error" if error else "no_features" if not len(points) else
            "low_count" if len(points) < config.minimum_features else
            "poor_coverage" if metrics["coverage"] < config.minimum_coverage else "ok")
        metrics["error"] = error
        return points, metrics

    def analyze(self, image, mode="both", render=False):
        if mode not in (*METHODS, "both"):
            raise ValueError("Invalid feature mode")
        rgb = np.asarray(image)
        if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
            raise ValueError("Expected uint8 RGB image")
        started = time.perf_counter_ns()
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        gray_ms = (time.perf_counter_ns()-started)/1e6
        methods = list(METHODS) if mode == "both" else [mode]
        # Alternate order so one detector does not always get the warm-cache advantage.
        if self.calls % 2:
            methods.reverse()
        results = {method: self.detect(gray, method) for method in methods}
        self.calls += 1
        metrics = {"gray_ms": gray_ms, "order": methods,
                   "detectors": {method: result[1] for method, result in results.items()}}
        output = self.overlay(rgb, results) if render else image
        return output, metrics

    def overlay(self, rgb, results):
        panels = []
        for method in METHODS:
            if method not in results:
                continue
            points, metrics = results[method]
            panel = rgb.copy()
            height, width = panel.shape[:2]
            color = (255, 215, 0) if method == "shi-tomasi" else (0, 230, 240)
            for column in range(1, self.config.grid_columns):
                x = width*column//self.config.grid_columns
                cv2.line(panel, (x, 0), (x, height-1), (75, 85, 95), 1)
            for row in range(1, self.config.grid_rows):
                y = height*row//self.config.grid_rows
                cv2.line(panel, (0, y), (width-1, y), (75, 85, 95), 1)
            for x, y in points:
                cv2.circle(panel, (round(float(x)), round(float(y))), 3, color, 1, cv2.LINE_AA)
            cv2.rectangle(panel, (0, 0), (width-1, 48), (16, 24, 32), -1)
            cv2.putText(panel, f"{method}: {metrics['count']} points | {metrics['detect_ms']:.2f} ms",
                (8, 19), cv2.FONT_HERSHEY_SIMPLEX, .47, color, 1, cv2.LINE_AA)
            cv2.putText(panel, f"grid {metrics['occupied_cells']}/{self.config.grid_rows*self.config.grid_columns} | {metrics['status']}",
                (8, 39), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1, cv2.LINE_AA)
            panels.append(panel)
        return Image.fromarray(np.concatenate(panels, axis=1))

    def metadata(self):
        return {"config": asdict(self.config), "opencv": cv2.__version__,
                "numpy": np.__version__, "timing": "detection call and point conversion; excludes grayscale, grid metrics, overlays, descriptors and tracking"}
