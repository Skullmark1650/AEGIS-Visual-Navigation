"""Laptop detector tests; optional laptop packages are not installed on the Pi."""
import unittest
from unittest.mock import patch

try:
    import cv2
    import numpy as np
    from laptop.feature_detector import DetectorSuite, FeatureConfig, distribution
    AVAILABLE = True
except ModuleNotFoundError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "Requires laptop OpenCV and NumPy dependencies")
class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.suite = DetectorSuite(FeatureConfig())

    def test_blank_image_has_no_features(self):
        for method in ("shi-tomasi", "orb"):
            points, metrics = self.suite.detect(np.zeros((240, 320), np.uint8), method)
            self.assertEqual(len(points), 0)
            self.assertEqual(metrics["coverage"], 0)
            self.assertEqual(metrics["status"], "no_features")

    def test_textured_image_has_bounded_in_image_points(self):
        image = np.random.default_rng(17).integers(0, 256, (480, 640), dtype=np.uint8)
        for method in ("shi-tomasi", "orb"):
            points, metrics = self.suite.detect(image, method)
            self.assertGreater(len(points), 30)
            self.assertLessEqual(len(points), 500)
            self.assertTrue(np.all(points >= 0))
            self.assertTrue(np.all(points[:, 0] < 640))
            self.assertTrue(np.all(points[:, 1] < 480))
            self.assertEqual(sum(metrics["grid_counts"]), len(points))

    def test_clustered_distribution_differs_from_full_coverage(self):
        points = np.array([[1, 1], [2, 2], [100, 100]], dtype=np.float32)
        result = distribution(points, (480, 640))
        self.assertEqual(result["occupied_cells"], 1)
        self.assertAlmostEqual(result["coverage"], 1/12)

    def test_invalid_parameters_and_inputs_rejected(self):
        for options in ({"shi_quality_level": 0}, {"orb_scale_factor": 1},
                        {"shi_block_size": 4}, {"shi_min_distance": float("nan")},
                        {"max_features": True}, {"minimum_features": 501}):
            with self.assertRaises(ValueError):
                FeatureConfig(**options)
        with self.assertRaises(ValueError):
            self.suite.detect(np.zeros((20, 20), np.float32), "orb")
        with self.assertRaises(ValueError):
            self.suite.detect(np.zeros((20, 20), np.uint8), "unknown")

    def test_detector_error_reported_as_error_not_empty_scene(self):
        with patch("laptop.feature_detector.cv2.goodFeaturesToTrack", side_effect=cv2.error("injected test failure")):
            with self.assertLogs("aegis.features", level="ERROR"):
                _, metrics = self.suite.detect(np.zeros((100, 100), np.uint8), "shi-tomasi")
        self.assertEqual(metrics["status"], "error")
        self.assertIn("injected test failure", metrics["error"])

    def test_comparison_uses_same_gray_and_alternates_order(self):
        image = np.zeros((240, 320, 3), np.uint8)
        seen = []
        original = self.suite.detect
        def inspect(gray, method):
            seen.append((id(gray), method))
            return original(gray, method)
        with patch.object(self.suite, "detect", side_effect=inspect):
            output, first = self.suite.analyze(image, render=True)
            _, second = self.suite.analyze(image)
        self.assertEqual(seen[0][0], seen[1][0])
        self.assertEqual(first["order"], ["shi-tomasi", "orb"])
        self.assertEqual(second["order"], ["orb", "shi-tomasi"])
        self.assertEqual(output.size, (640, 240))
        self.assertEqual(np.count_nonzero(image), 0)
