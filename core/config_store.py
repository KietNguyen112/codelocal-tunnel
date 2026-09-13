import base64
import json
import os
import sys
from typing import Any, Dict

try:
    import win32crypt
    HAS_DPAPI = True
except ImportError:
    HAS_DPAPI = False


def encrypt_secret(plain_text: str) -> str:
    """Encrypt a secret string using Windows DPAPI or base64 fallback."""
    if not plain_text:
        return ""
    data = plain_text.encode("utf-8")
    if HAS_DPAPI and sys.platform == "win32":
        try:
            encrypted = win32crypt.CryptProtectData(data, "codelocal_tunnel_secret", None, None, None, 0)
            return "dpapi:" + base64.b64encode(encrypted).decode("ascii")
        except Exception:
            pass
    # Obfuscation fallback
    b64 = base64.b64encode(data).decode("ascii")
    return "b64:" + b64


def decrypt_secret(cipher_text: str) -> str:
    """Decrypt a secret string previously encrypted."""
    if not cipher_text:
        return ""
    if cipher_text.startswith("dpapi:"):
        raw_b64 = cipher_text[6:]
        if HAS_DPAPI and sys.platform == "win32":
            try:
                raw = base64.b64decode(raw_b64.encode("ascii"))
                _, data = win32crypt.CryptUnprotectData(raw, None, None, None, 0)
                return data.decode("utf-8")
            except Exception:
                return ""
        return ""
    elif cipher_text.startswith("b64:"):
        raw_b64 = cipher_text[4:]
        try:
            return base64.b64decode(raw_b64.encode("ascii")).decode("utf-8")
        except Exception:
            return ""
    # Plaintext fallback for backward compatibility
    return cipher_text


class ConfigManager:
    """Manages persistent configuration for CodeLocal Tunnel."""

    DEFAULT_CONFIG = {
        "selected_mode": "cloudflare",  # "cloudflare" or "openai"
        "language": "vi",  # "vi" or "en"
        "theme": "dark",
        "auto_reconnect": True,
        "cloudflare": {
            "token": "",
            "hostname": "",
            "target_service": "backend",  # "backend" (3333), "web" (3000), "custom"
            "custom_port": 3333,
            "quick_tunnel": False,
        },
        "openai": {
            "tunnel_id": "",
            "runtime_api_key": "",
            "bearer_token": "",
            "alias": "codelocal-chatgpt",
            "local_mcp_url": "http://127.0.0.1:3333/mcp",
        },
        "codelocal": {
            "backend_port": 3333,
            "web_port": 3000,
            "auto_detect": True,
        },
    }

    def __init__(self, config_dir: str | None = None):
        if not config_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_dir = os.path.join(base_dir, "runtime")
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load configuration from file or return defaults."""
        config = self._deep_copy(self.DEFAULT_CONFIG)
        if os.path.isfile(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._deep_merge(config, saved)
            except Exception:
                pass
        return config

    def save(self) -> None:
        """Persist current configuration to disk."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}", file=sys.stderr)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self.data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        target = self.data
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    # Helper getters & setters for Cloudflare
    def get_cloudflare_token(self) -> str:
        encrypted = self.get("cloudflare.token", "")
        return decrypt_secret(encrypted).strip()

    def set_cloudflare_token(self, token: str) -> None:
        self.set("cloudflare.token", encrypt_secret(token.strip()))

    def get_cloudflare_hostname(self) -> str:
        raw = self.get("cloudflare.hostname", "").strip().lower()
        if raw.startswith("https://"):
            raw = raw[8:]
        elif raw.startswith("http://"):
            raw = raw[7:]
        return raw.split("/")[0].strip()

    def set_cloudflare_hostname(self, hostname: str) -> None:
        clean = hostname.strip().lower()
        if clean.startswith("https://"):
            clean = clean[8:]
        elif clean.startswith("http://"):
            clean = clean[7:]
        clean = clean.split("/")[0].strip()
        self.set("cloudflare.hostname", clean)

    def get_cloudflare_target_port(self) -> int:
        svc = self.get("cloudflare.target_service", "backend")
        if svc == "backend":
            return int(self.get("codelocal.backend_port", 3333))
        elif svc == "web":
            return int(self.get("codelocal.web_port", 3000))
        return int(self.get("cloudflare.custom_port", 3333))

    # Helper getters & setters for OpenAI
    def get_openai_tunnel_id(self) -> str:
        return self.get("openai.tunnel_id", "").strip().lower()

    def set_openai_tunnel_id(self, tunnel_id: str) -> None:
        self.set("openai.tunnel_id", tunnel_id.strip().lower())

    def get_openai_runtime_api_key(self) -> str:
        encrypted = self.get("openai.runtime_api_key", "")
        return decrypt_secret(encrypted).strip()

    def set_openai_runtime_api_key(self, api_key: str) -> None:
        self.set("openai.runtime_api_key", encrypt_secret(api_key.strip()))

    def get_openai_bearer_token(self) -> str:
        encrypted = self.get("openai.bearer_token", "")
        return decrypt_secret(encrypted).strip()

    def set_openai_bearer_token(self, token: str) -> None:
        self.set("openai.bearer_token", encrypt_secret(token.strip()))

    def get_openai_alias(self) -> str:
        return self.get("openai.alias", "codelocal-chatgpt").strip() or "codelocal-chatgpt"

    def set_openai_alias(self, alias: str) -> None:
        self.set("openai.alias", alias.strip())

    def get_openai_local_mcp_url(self) -> str:
        return self.get("openai.local_mcp_url", "http://127.0.0.1:3333/mcp").strip() or "http://127.0.0.1:3333/mcp"

    def set_openai_local_mcp_url(self, url: str) -> None:
        self.set("openai.local_mcp_url", url.strip())

    @staticmethod
    def _deep_copy(obj: Any) -> Any:
        return json.loads(json.dumps(obj))

    @staticmethod
    def _deep_merge(base: dict, incoming: dict) -> None:
        for k, v in incoming.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                ConfigManager._deep_merge(base[k], v)
            else:
                base[k] = v
