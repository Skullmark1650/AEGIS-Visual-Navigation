"""Stateful sparse pyramidal LK, quality gates, and independent feature renewal."""
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
if __package__:
    from .feature_detector import distribution
else:
    from feature_detector import distribution

LOG = logging.getLogger("aegis.flow")


@dataclass(frozen=True)
class FlowConfig:
    max_features: int = 300
    replenish_below: int = 120
    minimum_tracks: int = 30
    minimum_success_ratio: float = .5
    quality_level: float = .01
    min_distance: int = 10
    block_size: int = 7
    window_size: int = 21
    pyramid_max_level: int = 3
    max_iterations: int = 30
    epsilon: float = .01
    min_eigenvalue: float = .0001
    max_patch_error: float = 25
    max_forward_backward_px: float = 1
    max_flow_px: float = 80
    redetect_interval: int = 30
    minimum_coverage: float = .25
    max_frame_gap: int = 2
    max_interval_s: float = .3
    vector_display_scale: float = 3
    opencv_threads: int = 1

    def __post_init__(self):
        for key, low, high in [("max_features", 1, 3000), ("replenish_below", 1, 3000),
            ("minimum_tracks", 1, 3000), ("min_distance", 1, 100), ("block_size", 3, 31),
            ("window_size", 3, 101), ("pyramid_max_level", 0, 6),
            ("max_iterations", 1, 100), ("redetect_interval", 1, 1000),
            ("max_frame_gap", 0, 100), ("opencv_threads", 1, 16)]:
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"Invalid {key}")
        for key in ("minimum_success_ratio", "quality_level", "epsilon", "min_eigenvalue",
                    "max_patch_error", "max_forward_backward_px", "max_flow_px",
                    "minimum_coverage", "max_interval_s", "vector_display_scale"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid {key}")
        if any(getattr(self, key) > 1 for key in ("minimum_success_ratio", "quality_level", "minimum_coverage")):
            raise ValueError("Ratios must not exceed one")
        if self.block_size % 2 == 0 or self.window_size % 2 == 0:
            raise ValueError("Window and block sizes must be odd")
        if not self.minimum_tracks <= self.replenish_below <= self.max_features:
            raise ValueError("Require minimum_tracks <= replenish_below <= max_features")

    @classmethod
    def load(cls, path):
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


class OpticalFlowTracker:
    def __init__(self, config: FlowConfig):
        self.config = config
        cv2.setNumThreads(config.opencv_threads)
        self.previous = None
        self.points = np.empty((0, 2), np.float32)
        self.ids = np.empty(0, np.int64)
        self.next_id = 0
        self.last_info = None
        self.since_detection = 0
        self.last_previous = self.points.copy()
        self.last_current = self.points.copy()
        self.last_ids = self.ids.copy()

    def _renew(self, gray):
        """Exclude retained points; new features receive new monotonically unique IDs."""
        available = self.config.max_features-len(self.points)
        if available <= 0:
            return np.empty((0, 2), np.float32)
        mask = np.full(gray.shape, 255, np.uint8)
        for x, y in self.points:
            cv2.circle(mask, (round(float(x)), round(float(y))), self.config.min_distance, 0, -1)
        found = cv2.goodFeaturesToTrack(gray, maxCorners=available,
            qualityLevel=self.config.quality_level, minDistance=self.config.min_distance,
            blockSize=self.config.block_size, mask=mask, useHarrisDetector=False)
        added = found.reshape(-1, 2) if found is not None else np.empty((0, 2), np.float32)
        self.points = np.concatenate([self.points, added])
        self.ids = np.concatenate([self.ids, np.arange(self.next_id, self.next_id+len(added), dtype=np.int64)])
        self.next_id += len(added)
        return added

    def adopt_verified_points(self, points):
        """Seed current-image map observations; never invent previous-frame flow.

        Returns fresh IDs. The caller must supply geometrically verified points.
        Existing nearby seeds are displaced, not assigned a guessed map identity.
        """
        points=np.asarray(points,np.float32).reshape(-1,2)
        if self.previous is None or len(points)>self.config.max_features:
            raise ValueError('Invalid recovered point count/state')
        h,w=self.previous.shape
        if not np.isfinite(points).all() or np.any(points<0) or np.any(points[:,0]>=w) or np.any(points[:,1]>=h):
            raise ValueError('Recovered points outside current image')
        if len(points)>1:
            distances=np.linalg.norm(points[:,None]-points[None,:],axis=2)
            np.fill_diagonal(distances,np.inf)
            if np.min(distances)<2:raise ValueError('Duplicate recovered points')
        fresh=np.arange(self.next_id,self.next_id+len(points),dtype=np.int64)
        keep=np.ones(len(self.points),bool)
        if len(points) and len(self.points):
            keep=np.min(np.linalg.norm(self.points[:,None]-points[None,:],axis=2),axis=1)>=self.config.min_distance
        retained=np.flatnonzero(keep)[:self.config.max_features-len(points)]
        self.points=np.concatenate([points,self.points[retained]])
        self.ids=np.concatenate([fresh,self.ids[retained]])
        self.next_id+=len(points)
        return fresh

    def update(self, image, session: str, frame_id: int, sensor_ns: int, render=False):
        """Advance one observed image; new seeds never become fabricated correspondences."""
        started = time.perf_counter_ns()
        rgb = np.asarray(image)
        if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3 or not rgb.size:
            raise ValueError("Expected nonempty uint8 RGB image")
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        c = self.config
        reset = ""
        interval = None
        gap = 0
        if self.previous is None:
            reset = "startup"
        elif gray.shape != self.previous.shape:
            reset = "resolution_change"
        elif session != self.last_info[0]:
            reset = "session_change"
        else:
            interval = (sensor_ns-self.last_info[2])/1e9
            gap = frame_id-self.last_info[1]-1
            if frame_id <= self.last_info[1] or interval <= 0:
                reset = "nonmonotonic_frame"
            elif gap > c.max_frame_gap or interval > c.max_interval_s:
                reset = "frame_gap"
            elif not len(self.points):
                reset = "empty_tracks"
        if reset:
            self.points = np.empty((0, 2), np.float32)
            self.ids = np.empty(0, np.int64)
        attempted = len(self.points)
        previous_points = self.points.copy()
        previous_ids = self.ids.copy()
        new_points = np.empty((0, 2), np.float32)
        accepted_indices = np.empty(0, int)
        fb_accepted = np.empty(0)
        rejection = dict(forward=0, backward=0, consistency=0, motion=0, error=0)
        error = ""
        flow_started = time.perf_counter_ns()
        if attempted:
            settings = dict(winSize=(c.window_size, c.window_size), maxLevel=c.pyramid_max_level,
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, c.max_iterations, c.epsilon),
                minEigThreshold=c.min_eigenvalue)
            try:
                forward, status, residual = cv2.calcOpticalFlowPyrLK(
                    self.previous, gray, previous_points.reshape(-1, 1, 2), None, **settings)
                if forward is None or status is None or residual is None:
                    raise cv2.error("LK returned no forward result")
                forward = forward.reshape(-1, 2)
                height, width = gray.shape
                valid = status.ravel().astype(bool) & np.isfinite(forward).all(axis=1)
                valid &= np.isfinite(residual.ravel()) & (residual.ravel() <= c.max_patch_error)
                valid &= (forward[:, 0] >= 0) & (forward[:, 0] < width) & (forward[:, 1] >= 0) & (forward[:, 1] < height)
                indices = np.flatnonzero(valid)
                rejection["forward"] = attempted-len(indices)
                if len(indices):
                    backward, back_status, back_error = cv2.calcOpticalFlowPyrLK(
                        gray, self.previous, forward[indices].reshape(-1, 1, 2), None, **settings)
                    if backward is None or back_status is None or back_error is None:
                        raise cv2.error("LK returned no backward result")
                    backward = backward.reshape(-1, 2)
                    consistent = back_status.ravel().astype(bool) & np.isfinite(backward).all(axis=1)
                    consistent &= np.isfinite(back_error.ravel()) & (back_error.ravel() <= c.max_patch_error)
                    rejection["backward"] = len(indices)-int(consistent.sum())
                    fb = np.linalg.norm(backward-previous_points[indices], axis=1)
                    fb_good = consistent & (fb <= c.max_forward_backward_px)
                    rejection["consistency"] = int(consistent.sum())-int(fb_good.sum())
                    displacement = np.linalg.norm(forward[indices]-previous_points[indices], axis=1)
                    good = fb_good & (displacement <= c.max_flow_px)
                    rejection["motion"] = int(fb_good.sum())-int(good.sum())
                    accepted_indices = indices[good]
                    new_points = forward[accepted_indices]
                    fb_accepted = fb[good]
            except cv2.error as exc:
                LOG.exception("LK tracking failed")
                error = str(exc)
                rejection = dict(forward=0, backward=0, consistency=0, motion=0, error=attempted)
                accepted_indices = np.empty(0, int)
                new_points = np.empty((0, 2), np.float32)
        flow_ms = (time.perf_counter_ns()-flow_started)/1e6
        self.last_previous = previous_points[accepted_indices]
        self.last_current = new_points.copy()
        self.last_ids = previous_ids[accepted_indices]
        accepted = len(new_points)
        ratio = accepted/attempted if attempted else None
        lost = attempted > 0 and (accepted < c.minimum_tracks or ratio < c.minimum_success_ratio)
        self.points = new_points.copy()
        self.ids = self.last_ids.copy()
        if lost or error:
            self.points = np.empty((0, 2), np.float32)
            self.ids = np.empty(0, np.int64)
            reset = "tracking_quality" if not error else "tracking_error"
        spread = distribution(self.points, gray.shape)
        self.since_detection += 1
        replenish = bool(reset or len(self.points) < c.replenish_below or
                         spread["coverage"] < c.minimum_coverage or self.since_detection >= c.redetect_interval)
        added = np.empty((0, 2), np.float32)
        renew_started = time.perf_counter_ns()
        if replenish:
            try:
                added = self._renew(gray)
            except cv2.error as exc:
                LOG.exception("Feature replacement failed")
                error = str(exc)
            self.since_detection = 0
        renewal_ms = (time.perf_counter_ns()-renew_started)/1e6
        vectors = self.last_current-self.last_previous
        magnitude = np.linalg.norm(vectors, axis=1)
        metrics = {"attempted": attempted, "tracked": accepted, "success_ratio": ratio,
            "active": len(self.points), "added": len(added), "replacement_event": bool(len(added)),
            "redetection_attempt": replenish, "reset_reason": reset, "frame_gap": max(0, gap),
            "interval_s": interval, "mean_flow_px": float(magnitude.mean()) if accepted else None,
            "median_dx_px": float(np.median(vectors[:, 0])) if accepted else None,
            "median_dy_px": float(np.median(vectors[:, 1])) if accepted else None,
            "flow_spread_px": float(np.sqrt(np.mean(np.sum((vectors-vectors.mean(axis=0))**2, axis=1)))) if accepted else None,
            "mean_fb_error_px": float(fb_accepted.mean()) if accepted and len(fb_accepted) else None,
            "flow_ms": flow_ms, "renewal_ms": renewal_ms,
            "coverage": distribution(self.points, gray.shape)["coverage"],
            "status": "error" if error else "no_features" if not len(self.points) else
                      "reinitialized" if lost else "initializing" if not attempted else
                      "degraded" if accepted < c.replenish_below or spread["coverage"] < c.minimum_coverage else "tracking",
            "error": error, **{f"rejected_{key}": value for key, value in rejection.items()}}
        self.previous = gray.copy()
        self.last_info = (session, frame_id, sensor_ns)
        metrics["total_ms"] = (time.perf_counter_ns()-started)/1e6
        output = self.overlay(rgb, added, metrics) if render else image
        return output, metrics

    def overlay(self, rgb, added, metrics):
        panel = rgb.copy()
        for old, new in zip(self.last_previous, self.last_current):
            end = old+(new-old)*self.config.vector_display_scale
            cv2.arrowedLine(panel, tuple(np.rint(old).astype(int)), tuple(np.rint(end).astype(int)),
                            (70, 255, 110), 1, cv2.LINE_AA, tipLength=.3)
            cv2.circle(panel, tuple(np.rint(new).astype(int)), 2, (255, 220, 60), -1)
        for point in added:
            cv2.circle(panel, tuple(np.rint(point).astype(int)), 3, (0, 220, 255), 1)
        cv2.rectangle(panel, (0, 0), (panel.shape[1]-1, 54), (16, 24, 32), -1)
        success = f"{metrics['success_ratio']*100:.1f}%" if metrics['success_ratio'] is not None else "N/A"
        cv2.putText(panel, f"Pyr LK | {metrics['status']} | {metrics['tracked']}/{metrics['attempted']} ({success})",
                    (8, 20), cv2.FONT_HERSHEY_SIMPLEX, .48, (180, 250, 210), 1, cv2.LINE_AA)
        cv2.putText(panel, f"Active {metrics['active']} | new {metrics['added']} | vectors x{self.config.vector_display_scale:g} display only",
                    (8, 42), cv2.FONT_HERSHEY_SIMPLEX, .45, (180, 250, 210), 1, cv2.LINE_AA)
        return Image.fromarray(panel)

    def metadata(self):
        return {"config": asdict(self.config), "opencv": cv2.__version__, "numpy": np.__version__,
                "note": "Accepted sparse image correspondences only; no camera pose, scale, or physical velocity"}
