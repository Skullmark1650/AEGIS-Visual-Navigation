import io
import unittest
from laptop.camera_client import read_frame
from pi.camera_server import load_config


class ProtocolTests(unittest.TestCase):
    def test_binary_payload_uses_length_not_boundary(self):
        payload = b"JPEG\r\n--frame\r\nbytes"
        stream = io.BytesIO(b"--frame\r\nContent-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload + b"\r\n")
        self.assertEqual(read_frame(stream)[1], payload)

    def test_truncated_payload_rejected(self):
        with self.assertRaises(ValueError):
            read_frame(io.BytesIO(b"--frame\r\nContent-Length: 200\r\n\r\nshort"))

    def test_excessive_allocation_rejected(self):
        with self.assertRaises(ValueError):
            read_frame(io.BytesIO(b"--frame\r\nContent-Length: 9000000\r\n\r\n"))

    def test_stream_config(self):
        self.assertEqual(load_config("configs/stream.json")["fps"], 15)
