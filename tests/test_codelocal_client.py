import os
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

from core.codelocal_client import CodeLocalDetector


class MockCodeLocalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-CodeLocal-Gateway", "test-gateway-instance-123")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b'<html>CodeLocal Web</html>')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet during tests


class TestCodeLocalClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 19333), MockCodeLocalHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_detector_health_check_success(self):
        det = CodeLocalDetector()
        res = det.check_backend_status(port=19333, timeout=1.0)
        self.assertTrue(res["running"])
        self.assertEqual(res["status_code"], 200)
        self.assertEqual(res["gateway_id"], "test-gateway-instance-123")

    def test_detector_health_check_offline(self):
        det = CodeLocalDetector()
        # Use a port that should not have anything listening
        res = det.check_backend_status(port=19399, timeout=0.5)
        self.assertFalse(res["running"])
        self.assertEqual(res["status_code"], 0)

    def test_web_check_success(self):
        det = CodeLocalDetector()
        ok = det.check_web_status(port=19333, timeout=1.0)
        self.assertTrue(ok)

    def test_generate_local_bearer_token(self):
        token = CodeLocalDetector.generate_local_bearer_token()
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 50)
        self.assertIn(".", token)
        parts = token.split(".")
        self.assertEqual(len(parts), 2)


if __name__ == "__main__":
    unittest.main()
