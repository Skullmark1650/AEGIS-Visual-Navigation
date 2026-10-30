import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from laptop.camera_client import Receiver


class FinalControlTests(unittest.TestCase):
    def test_status_is_atomic_and_stop_requests_graceful_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            receiver=Receiver(SimpleNamespace(status_file=root/'live.json',stop_file=root/'stop'))
            self.assertFalse(receiver.should_stop())
            receiver.publish_status(dict(frame_id=4,vo_status='map_tracking'))
            status=json.loads((root/'live.json').read_text())
            self.assertEqual(status['row']['frame_id'],4)
            self.assertFalse((root/'live.tmp').exists())
            (root/'stop').touch()
            self.assertTrue(receiver.should_stop())
            self.assertTrue(receiver.stop.is_set())

    def test_optional_controls_preserve_normal_receiver(self):
        receiver=Receiver(SimpleNamespace())
        receiver.publish_status(dict(frame_id=1))
        self.assertFalse(receiver.should_stop())
