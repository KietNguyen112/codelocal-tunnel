import os
import shutil
import tempfile
import unittest

from core.config_store import ConfigManager, decrypt_secret, encrypt_secret


class TestConfigStore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cfg = ConfigManager(config_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_encryption_roundtrip(self):
        plain = "eyJhIjoiY2xvdWRmbGFyZS1zZWNyZXQtdG9rZW4ifQ=="
        enc = encrypt_secret(plain)
        self.assertNotEqual(plain, enc)
        dec = decrypt_secret(enc)
        self.assertEqual(plain, dec)

    def test_empty_encryption(self):
        self.assertEqual(encrypt_secret(""), "")
        self.assertEqual(decrypt_secret(""), "")

    def test_cloudflare_config(self):
        token = "test_cf_token_xyz"
        host = "https://mcp.mycustomdomain.com/some/path"
        self.cfg.set_cloudflare_token(token)
        self.cfg.set_cloudflare_hostname(host)
        self.cfg.set("cloudflare.target_service", "backend")

        self.assertEqual(self.cfg.get_cloudflare_token(), token)
        self.assertEqual(self.cfg.get_cloudflare_hostname(), "mcp.mycustomdomain.com")
        self.assertEqual(self.cfg.get_cloudflare_target_port(), 3333)

    def test_openai_config(self):
        tid = "tunnel_0123456789abcdef0123456789abcdef"
        key = "sk-mcp-testkey123"
        self.cfg.set_openai_tunnel_id(tid)
        self.cfg.set_openai_runtime_api_key(key)
        self.cfg.set_openai_alias("my-alias")
        self.cfg.set_openai_local_mcp_url("http://127.0.0.1:3333/mcp")

        self.assertEqual(self.cfg.get_openai_tunnel_id(), tid)
        self.assertEqual(self.cfg.get_openai_runtime_api_key(), key)
        self.assertEqual(self.cfg.get_openai_alias(), "my-alias")
        self.assertEqual(self.cfg.get_openai_local_mcp_url(), "http://127.0.0.1:3333/mcp")

    def test_openai_bearer_token_encryption(self):
        token = "eyJ0eXAiOiJhY2Nlc3MiLCJzdWIiOiJ1c3JfdGsxNzExMjAwMiJ9.mock_signature"
        self.cfg.set_openai_bearer_token(token)
        self.assertEqual(self.cfg.get_openai_bearer_token(), token)
        # Verify it is not stored in plaintext in the raw dictionary
        raw_val = self.cfg.get("openai.bearer_token")
        self.assertNotEqual(raw_val, token)

    def test_persistence_reloading(self):
        self.cfg.set_cloudflare_hostname("test.domain.com")
        self.cfg.set_openai_tunnel_id("tunnel_11111111111111111111111111111111")
        self.cfg.save()

        # Reload from same dir
        reloaded = ConfigManager(config_dir=self.test_dir)
        self.assertEqual(reloaded.get_cloudflare_hostname(), "test.domain.com")
        self.assertEqual(reloaded.get_openai_tunnel_id(), "tunnel_11111111111111111111111111111111")

    def test_tunnel_id_case_and_space_normalization(self):
        self.cfg.set_openai_tunnel_id("  TUNNEL_3C8E41A9BF974BFA856E187F583E74A1  ")
        self.assertEqual(self.cfg.get_openai_tunnel_id(), "tunnel_3c8e41a9bf974bfa856e187f583e74a1")

    def test_hostname_normalization(self):
        self.cfg.set_cloudflare_hostname("  HTTPS://MCP.MYDOMAIN.COM/mcp/extra  ")
        self.assertEqual(self.cfg.get_cloudflare_hostname(), "mcp.mydomain.com")


if __name__ == "__main__":
    unittest.main()
