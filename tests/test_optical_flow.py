import unittest
from unittest.mock import patch
try:
    import cv2
    import numpy as np
    from laptop.optical_flow import OpticalFlowTracker, FlowConfig
    AVAILABLE = True
except ModuleNotFoundError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "Requires laptop OpenCV and NumPy")
class OpticalFlowTests(unittest.TestCase):
    def setUp(self):
        gray = np.random.default_rng(23).integers(0, 256, (240, 320), dtype=np.uint8)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        self.image = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        self.tracker = OpticalFlowTracker(FlowConfig())

    def step(self, image, frame, session="test"):
        return self.tracker.update(image, session, frame, frame*66_666_667)

    def test_known_translation_and_unique_ids(self):
        _, initial = self.step(self.image, 1)
        self.assertIsNone(initial["success_ratio"])
        moved = cv2.warpAffine(self.image, np.float32([[1, 0, 4], [0, 1, 3]]), (320, 240))
        _, metrics = self.step(moved, 2)
        # Finite-image borders and coarse noise texture can be rejected by LK.
        # Validate retained correspondence accuracy rather than assuming 80% survival.
        self.assertGreater(metrics["tracked"], 100)
        vectors = self.tracker.last_current-self.tracker.last_previous
        self.assertLess(float(np.median(np.linalg.norm(vectors-[4, 3], axis=1))), .1)
        self.assertEqual(len(set(self.tracker.ids)), len(self.tracker.ids))
        self.assertEqual(metrics["tracked"]+sum(metrics[f"rejected_{key}"] for key in ["forward", "backward", "consistency", "motion", "error"]), metrics["attempted"])

    def test_stationary_tracks_and_non_destructive_overlay(self):
        self.step(self.image, 1)
        before = self.image.copy()
        output, metrics = self.tracker.update(self.image, "test", 2, 133333334, render=True)
        self.assertGreater(metrics["success_ratio"], .95)
        self.assertLess(metrics["mean_flow_px"], .01)
        np.testing.assert_array_equal(self.image, before)
        self.assertEqual(output.size, (320, 240))

    def test_loss_and_replacement_do_not_fabricate_correspondences(self):
        self.step(self.image, 1)
        _, blank = self.step(np.full_like(self.image, 128), 2)
        self.assertEqual(blank["tracked"], 0)
        self.assertEqual(blank["active"], 0)
        self.assertEqual(blank["status"], "no_features")
        _, restored = self.step(self.image, 3)
        self.assertGreater(restored["added"], 100)
        self.assertEqual(restored["tracked"], 0)
        self.assertIsNone(restored["success_ratio"])
        self.assertEqual(len(self.tracker.last_current), 0)
        _, resumed = self.step(self.image, 4)
        self.assertGreater(resumed["success_ratio"], .95)

    def test_periodic_renewal_preserves_survivors(self):
        self.tracker = OpticalFlowTracker(FlowConfig(redetect_interval=1))
        self.step(self.image, 1)
        old_ids = set(self.tracker.ids)
        occluded = self.image.copy()
        occluded[:60, :80] = 128
        _, metrics = self.step(occluded, 2)
        self.assertTrue(metrics["redetection_attempt"])
        self.assertGreater(metrics["added"], 0)
        self.assertEqual(metrics["reset_reason"], "")
        self.assertTrue(set(self.tracker.last_ids).issubset(set(self.tracker.ids)))
        added_ids = set(self.tracker.ids)-set(self.tracker.last_ids)
        self.assertTrue(added_ids.isdisjoint(old_ids))
        new_points = self.tracker.points[-metrics["added"]:]
        distances = np.linalg.norm(new_points[:, None, :]-self.tracker.last_current[None, :, :], axis=2)
        self.assertGreaterEqual(float(distances.min()), 9)
        self.assertLessEqual(metrics["active"], self.tracker.config.max_features)

    def test_session_time_and_resolution_resets(self):
        self.step(self.image, 1)
        _, changed = self.step(self.image, 2, "different")
        self.assertEqual(changed["reset_reason"], "session_change")
        self.assertEqual(changed["attempted"], 0)
        _, gap = self.step(self.image, 20, "different")
        self.assertEqual(gap["reset_reason"], "frame_gap")
        self.assertEqual(gap["tracked"], 0)
        _, resized = self.step(self.image[:100, :100], 21, "different")
        self.assertEqual(resized["reset_reason"], "resolution_change")
        _, repeated = self.step(self.image[:100, :100], 21, "different")
        self.assertEqual(repeated["reset_reason"], "nonmonotonic_frame")
        self.assertEqual(repeated["tracked"], 0)

    def test_forward_backward_rejects_inconsistent_returns(self):
        self.step(self.image, 1)
        original = cv2.calcOpticalFlowPyrLK
        calls = 0
        def inconsistent(*args, **kwargs):
            nonlocal calls
            result = original(*args, **kwargs)
            calls += 1
            if calls == 2:
                return result[0]+5, result[1], result[2]
            return result
        with patch("laptop.optical_flow.cv2.calcOpticalFlowPyrLK", side_effect=inconsistent):
            _, metrics = self.step(self.image, 2)
        self.assertEqual(metrics["tracked"], 0)
        self.assertGreater(metrics["rejected_consistency"], 100)
        self.assertEqual(metrics["reset_reason"], "tracking_quality")

    def test_invalid_config_and_image(self):
        for settings in ({"window_size": 20}, {"max_interval_s": float("nan")},
                         {"minimum_success_ratio": 2}, {"max_features": 20}):
            with self.assertRaises(ValueError):
                FlowConfig(**settings)
        with self.assertRaises(ValueError):
            self.step(np.zeros((10, 10), np.uint8), 1)

    def test_lk_exception_is_reported_and_reinitialized(self):
        self.step(self.image, 1)
        with patch("laptop.optical_flow.cv2.calcOpticalFlowPyrLK", side_effect=cv2.error("test exception")):
            with self.assertLogs("aegis.flow", level="ERROR"):
                _, metrics = self.step(self.image, 2)
        self.assertEqual(metrics["status"], "error")
        self.assertEqual(metrics["tracked"], 0)
        self.assertGreater(metrics["added"], 100)
        self.assertEqual(metrics["rejected_error"], metrics["attempted"])
