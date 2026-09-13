import os
import re
import shutil
import tempfile
import unittest

from core.tunnel_runner import TunnelManager


class TestTunnelRunner(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.mgr = TunnelManager(base_dir=self.test_dir)

    def tearDown(self):
        if self.mgr.running:
            self.mgr.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_binaries_detection_on_real_dir(self):
        # Point to the actual tunnel directory
        real_tunnel_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        real_mgr = TunnelManager(base_dir=real_tunnel_dir)
        bins = real_mgr.check_binaries()

        self.assertTrue(bins["cloudflared"]["found"])
        self.assertTrue(bins["tunnel_client"]["found"])
        self.assertIn("2025.", bins["cloudflared"]["version"])
        self.assertIn("0.0.13", bins["tunnel_client"]["version"])

    def test_secret_redaction(self):
        self.mgr._active_secrets = ["super_secret_token_abc", "sk-mcp-another-secret"]
        log_line = "Failed to connect with super_secret_token_abc and key sk-mcp-another-secret"
        redacted = self.mgr._redact(log_line)

        self.assertNotIn("super_secret_token_abc", redacted)
        self.assertNotIn("sk-mcp-another-secret", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_openai_id_validation(self):
        valid_id = "tunnel_3c8e41a9bf974bfa856e187f583e74a1"
        self.assertTrue(bool(re.fullmatch(r"tunnel_[0-9a-f]{32}", valid_id)))

        invalid_ids = [
            "tunnel_xyz",
            "tunnel_3c8e41a9bf974bfa856e187f583e74a",  # 31 chars
            "tunnel_3c8e41a9bf974bfa856e187f583e74a12",  # 33 chars
            "tunnel_3C8E41A9BF974BFA856E187F583E74A1",  # uppercase
            "other_3c8e41a9bf974bfa856e187f583e74a1",
        ]
        for inv in invalid_ids:
            self.assertFalse(bool(re.fullmatch(r"tunnel_[0-9a-f]{32}", inv)), f"Expected invalid: {inv}")

    def test_uptime_formatting(self):
        self.mgr.running = False
        self.assertEqual(self.mgr.get_uptime_str(), "--:--:--")

        self.mgr.running = True
        self.mgr.started_at = 1000.0
        # Mock current time
        import time
        orig_time = time.time
        try:
            time.time = lambda: 1000.0 + 3665  # 1 hour, 1 min, 5 secs
            self.assertEqual(self.mgr.get_uptime_str(), "01:01:05")
        finally:
            time.time = orig_time

    def test_admin_ui_url_extraction(self):
        self.mgr.running = True
        # Mock process output containing Web UI line
        class MockProcess:
            def __init__(self, lines):
                import io
                self.stdout = io.StringIO("\n".join(lines) + "\n")
                self.pid = 99999
            def poll(self):
                return 0
            def terminate(self):
                pass

        log_lines = [
            'time=2026-09-14T03:36:11.290+07:00 level=INFO msg="🌐 WEB UI: http://127.0.0.1:59426/ui"',
            'time=2026-09-14T03:36:11.290+07:00 level=INFO msg="🟢 tunnel-client started" tunnel_url=https://api.openai.com/v1/tunnel/tunnel_123',
        ]
        self.mgr.process = MockProcess(log_lines)
        self.mgr._read_oa_output()

        self.assertEqual(self.mgr.admin_ui_url, "http://127.0.0.1:59426/ui")
        self.assertEqual(self.mgr.current_state, TunnelManager.STATE_ACTIVE)

    def test_openai_401_error_handling(self):
        self.mgr.running = True
        class MockProcess:
            def __init__(self, lines):
                import io
                self.stdout = io.StringIO("\n".join(lines) + "\n")
                self.pid = 99999
            def poll(self):
                return 0
            def terminate(self):
                pass

        log_lines = [
            'time=2026-09-14T03:36:11.634+07:00 level=WARN msg="poll failed; backing off" status_code=401 status="401 Unauthorized"',
        ]
        self.mgr.process = MockProcess(log_lines)
        self.mgr._read_oa_output()

        self.assertTrue(self.mgr._fatal_error)
        self.assertEqual(self.mgr.current_state, TunnelManager.STATE_ERROR)
        self.assertIn("401 Unauthorized", self.mgr.status_message)

    def test_upstream_mcp_401_does_not_kill_tunnel(self):
        self.mgr.running = True
        self.mgr._set_state(TunnelManager.STATE_ACTIVE, "tunnel://tunnel_6aa70d7ea66c8191aeb906f323541152")

        class MockProcess:
            def __init__(self, lines):
                import io
                self.stdout = io.StringIO("\n".join(lines) + "\n")
                self.pid = 99999
            def poll(self):
                return 0
            def terminate(self):
                pass

        log_lines = [
            'time=2026-09-14T03:58:50.770+07:00 level=WARN msg="dispatcher received MCP upstream error; posted error response to control plane" client_instance_id=02001885164ce4e21ba326f925519684 tunnel_id=tunnel_6aa70d7ea66c8191aeb906f323541152 component=dispatcher request_id=cmd_1ba16a6b_a798_40f3_800c_bc99ccc360c0 cmd_request_id=7fb25a8a-2bf6-47aa-956d-9a75f4ee3d47/jla4 rpc_request_id=openai-mcp-discover status_code=401 channel=main rpc_method=server/discover failure_source=target_http transport_error_kind=invalid_mcp_error upstream_response_received=true tunnel_client_version=0.0.13+4b5267f823be0b046bb883aacb51603cfde3a0ea upstream_status=401 response_content_type="application/json; charset=utf-8" tunnel_request_id=req_a5db8445460644f69609fb0e77b27e27'
        ]
        self.mgr.process = MockProcess(log_lines)
        self.mgr._read_oa_output()

        self.assertFalse(self.mgr._fatal_error)
        self.assertNotEqual(self.mgr.current_state, TunnelManager.STATE_ERROR)
        self.assertEqual(self.mgr.current_state, TunnelManager.STATE_ACTIVE)

    def test_cloudflare_invalid_token_error_handling(self):
        self.mgr.running = True
        class MockProcess:
            def __init__(self, lines):
                import io
                self.stdout = io.StringIO("\n".join(lines) + "\n")
                self.pid = 99999
            def poll(self):
                return 0
            def terminate(self):
                pass

        log_lines = [
            'Provided Tunnel token is not valid.',
        ]
        self.mgr.process = MockProcess(log_lines)
        self.mgr._read_cf_output()

        self.assertTrue(self.mgr._fatal_error)
        self.assertEqual(self.mgr.current_state, TunnelManager.STATE_ERROR)
        self.assertIn("không hợp lệ", self.mgr.status_message)

    def test_i18n_dictionary_symmetry(self):
        from ui.theme import I18N
        vi_keys = set(I18N["vi"].keys())
        en_keys = set(I18N["en"].keys())
        self.assertEqual(vi_keys, en_keys, f"Mismatched keys: {vi_keys ^ en_keys}")

    def test_run_doctor_output(self):
        report = self.mgr.run_doctor()
        self.assertIsInstance(report, list)
        self.assertTrue(len(report) >= 3)
        self.assertTrue(any("DOCTOR" in line for line in report))
        self.assertTrue(any("cloudflared" in line for line in report))


if __name__ == "__main__":
    unittest.main()
