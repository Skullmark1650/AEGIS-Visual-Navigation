"""Hardware-independent checks; real capture is a separate integration test."""
import tempfile
import unittest
from pathlib import Path
from pi.capture_test import capture
from scripts.verify_environment import inspect_environment


class PhaseZeroTests(unittest.TestCase):
    def test_invalid_dimensions_rejected_without_camera(self):
        with self.assertRaises(ValueError):
            capture(Path("never-created.jpg"), width=0)

    def test_invalid_extension_rejected_without_camera(self):
        with self.assertRaises(ValueError):
            capture(Path("never-created.png"))

    def test_existing_capture_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "existing.jpg"
            image.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                capture(image)
            self.assertEqual(image.read_bytes(), b"original")

    def test_invalid_role_rejected(self):
        with self.assertRaises(ValueError):
            inspect_environment("unknown")


if __name__ == "__main__":
    unittest.main()
