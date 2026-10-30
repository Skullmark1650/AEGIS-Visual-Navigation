import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
try:
    import cv2
    import numpy as np
    from PIL import Image
    from laptop.camera_calibration import (BoardConfig, object_points, inspect_board,
        corner_distance, calibrate_points, undistort_rgb, verify_profile)
    from laptop.calibration_capture import CaptureSession
    from laptop.verify_calibration import synthetic_observations
    AVAILABLE = True
except ModuleNotFoundError:
    AVAILABLE = False


def test_profile(size=(640, 480), lens=2.0):
    content = {"camera_id": "synthetic-test-device", "camera_model": "test",
        "image_size": list(size), "main_format": "BGR888", "raw_size": [1536, 864],
        "raw_format": "test", "transform": "identity", "scaler_crop": [0, 0, 640, 480],
        "focus_mode": "manual", "lens_position": lens}
    return {"profile": content, "profile_id": hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()}


@unittest.skipUnless(AVAILABLE, "Requires optional laptop calibration dependencies")
class CalibrationTests(unittest.TestCase):
    @staticmethod
    def pattern():
        image = np.full((480, 640, 3), 255, np.uint8)
        for row in range(7):
            for column in range(10):
                if (row+column) % 2 == 0:
                    image[135+row*30:135+(row+1)*30, 170+column*30:170+(column+1)*30] = 0
        return Image.fromarray(image)

    def test_detects_correct_pattern_and_rejects_blank(self):
        corners, quality = inspect_board(self.pattern(), BoardConfig())
        self.assertEqual(corners.shape, (54, 2))
        self.assertTrue(quality["accepted"], quality)
        corners, quality = inspect_board(Image.new("RGB", (640, 480), "white"), BoardConfig())
        self.assertIsNone(corners)
        self.assertFalse(quality["accepted"])

    def test_known_camera_parameters_and_heldout_fit(self):
        board, matrix, _, observations = synthetic_observations()
        result = calibrate_points(observations, (640, 480), board, 20, source_kind="synthetic", profile=None)
        self.assertLess(float(np.abs(np.asarray(result["camera_matrix"])-matrix).max()), 3)
        self.assertLess(result["training_rms_px"], .2)
        self.assertLess(result["heldout_mean_rms_px"], .2)
        self.assertTrue(result["numerical_checks_passed"], result["warnings"])
        self.assertEqual(sum(view["split"] == "holdout" for view in result["per_view"]), 6)
        self.assertEqual(result["source_kind"], "synthetic")

    def test_duplicates_and_too_few_views_rejected(self):
        corners, _ = inspect_board(self.pattern(), BoardConfig())
        with self.assertRaises(ValueError):
            calibrate_points([corners], (640, 480), BoardConfig(), 20, source_kind="synthetic", profile=None)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            calibrate_points([corners]*20, (640, 480), BoardConfig(), 20, source_kind="synthetic", profile=None)
        self.assertEqual(corner_distance(corners, corners[::-1]), 0)

    def test_capture_preserves_source_and_rejects_duplicate_or_focus_change(self):
        image = self.pattern()
        corners, quality = inspect_board(image, BoardConfig())
        profile = test_profile()
        frame = dict(camera_profile_id=profile["profile_id"], focus_mode="manual", lens_position=2.0,
                     frame_id=1, session="synthetic-unit-test", sensor_ns=1)
        with tempfile.TemporaryDirectory() as directory:
            session = CaptureSession(Path(directory)/"session", BoardConfig(), profile)
            name = session.save(image, corners, quality, frame)
            self.assertTrue((session.directory/name).exists())
            self.assertEqual(len(session.manifest["views"]), 1)
            with self.assertRaisesRegex(ValueError, "similar"):
                session.save(image, corners, quality, frame)
            frame["lens_position"] = 3.0
            with self.assertRaisesRegex(ValueError, "lens"):
                session.save(image, corners, quality, frame)
            frame["lens_position"] = float("nan")
            with self.assertRaises(ValueError):
                session.save(image, corners, quality, frame)

    def test_resume_preserves_images_numbering_and_rejects_tampering(self):
        image = self.pattern()
        corners, quality = inspect_board(image, BoardConfig())
        profile = test_profile()
        frame = dict(camera_profile_id=profile["profile_id"], focus_mode="manual", lens_position=2.0,
                     frame_id=1, session="test", sensor_ns=1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"session"
            original = CaptureSession(path, BoardConfig(), profile)
            original.save(image, corners, quality, frame)
            first = (path/"view-0001.png").read_bytes()
            resumed = CaptureSession(path, BoardConfig(), profile, resume=True)
            self.assertEqual(len(resumed.corners), 1)
            shifted = Image.fromarray(np.roll(np.asarray(image), 30, axis=1))
            points, checks = inspect_board(shifted, BoardConfig())
            self.assertEqual(resumed.save(shifted, points, checks, frame), "view-0002.png")
            self.assertEqual((path/"view-0001.png").read_bytes(), first)
            with self.assertRaises(ValueError):
                CaptureSession(path, BoardConfig(), test_profile(lens=3), resume=True)
            (path/"view-0001.png").write_bytes(first+b"tampered")
            with self.assertRaisesRegex(ValueError, "integrity"):
                CaptureSession(path, BoardConfig(), profile, resume=True)

    def test_undistortion_and_synthetic_boundary(self):
        image = np.asarray(self.pattern())
        calibration = {"source_kind": "synthetic", "camera_profile": None, "image_size": [640, 480],
            "camera_matrix": [[530, 0, 320], [0, 525, 240], [0, 0, 1]], "distortion": [0]*5,
            "numerical_checks_passed": True, "requires_visual_review": True}
        with self.assertRaisesRegex(ValueError, "Synthetic"):
            undistort_rgb(image, calibration, None)
        output = undistort_rgb(image, calibration, None, allow_synthetic=True, allow_candidate=True)
        np.testing.assert_array_equal(image, output)
        with self.assertRaisesRegex(ValueError, "resolution"):
            undistort_rgb(image[:100], calibration, None, allow_synthetic=True, allow_candidate=True)

    def test_profile_integrity_and_mismatch(self):
        profile = test_profile()
        verify_profile(profile)
        changed = copy.deepcopy(profile)
        changed["profile"]["lens_position"] = 3.0
        with self.assertRaises(ValueError): verify_profile(changed)
        calibration = {"source_kind": "real_camera", "camera_profile": profile, "image_size": [640, 480],
            "camera_matrix": [[530, 0, 320], [0, 525, 240], [0, 0, 1]], "distortion": [0]*5,
            "numerical_checks_passed": True, "requires_visual_review": True}
        with self.assertRaisesRegex(ValueError, "mismatch"):
            undistort_rgb(np.asarray(self.pattern()), calibration, test_profile(lens=3.0), allow_candidate=True)

    def test_parameter_and_quality_rejection(self):
        for options in ({"columns": True}, {"rows": 2}, {"minimum_board_area": 2}, {"maximum_rms_px": float("nan")}):
            with self.assertRaises(ValueError): BoardConfig(**options)
        with self.assertRaises(ValueError): object_points(BoardConfig(), -1)
        corners, quality = inspect_board(self.pattern(), BoardConfig(minimum_sharpness=1e9))
        self.assertIsNotNone(corners)
        self.assertFalse(quality["accepted"])
