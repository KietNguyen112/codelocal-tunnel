import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class CodeLocalDetector:
    """Detects and monitors the status of the local CodeLocal instance."""

    def __init__(self, base_dir: Optional[str] = None):
        if not base_dir:
            # Assumes tunnel is adjacent to codelocal: <workspace>/tunnel -> <workspace>/codelocal
            tunnel_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            workspace_dir = os.path.dirname(tunnel_dir)
            candidate = os.path.join(workspace_dir, "codelocal")
            if os.path.isdir(candidate):
                self.codelocal_dir = candidate
            else:
                self.codelocal_dir = workspace_dir
        else:
            self.codelocal_dir = base_dir

    def check_backend_status(self, port: int = 3333, timeout: float = 1.2) -> Dict[str, Any]:
        """Check if CodeLocal Cloud Backend is alive on http://127.0.0.1:<port>/health."""
        url = f"http://127.0.0.1:{port}/health"
        result = {
            "running": False,
            "port": port,
            "status_code": 0,
            "gateway_id": "",
            "response": "",
            "mcp_url": f"http://127.0.0.1:{port}/mcp",
        }
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CodeLocal-Tunnel-Probe/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result["status_code"] = resp.status
                result["running"] = (resp.status == 200)
                body = resp.read().decode("utf-8", errors="replace")
                result["response"] = body
                gateway_hdr = resp.headers.get("X-CodeLocal-Gateway", "")
                if gateway_hdr:
                    result["gateway_id"] = gateway_hdr
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        return result

    def check_web_status(self, port: int = 3000, timeout: float = 1.2) -> bool:
        """Check if CodeLocal Web Frontend is alive on http://127.0.0.1:<port>."""
        url = f"http://127.0.0.1:{port}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CodeLocal-Tunnel-Probe/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status in (200, 301, 302, 304, 307, 308)
        except Exception:
            return False

    def check_all(self, backend_port: int = 3333, web_port: int = 3000) -> Dict[str, Any]:
        backend = self.check_backend_status(backend_port)
        web_running = self.check_web_status(web_port)
        return {
            "backend_running": backend["running"],
            "web_running": web_running,
            "backend_port": backend_port,
            "web_port": web_port,
            "mcp_url": backend["mcp_url"],
            "gateway_id": backend["gateway_id"],
        }

    def launch_backend(self) -> bool:
        """Attempt to launch CodeLocal Cloud Backend in a new window."""
        run_script = os.path.join(self.codelocal_dir, "scripts", "run-backend.bat")
        if os.path.isfile(run_script):
            try:
                if sys.platform == "win32":
                    subprocess.Popen(
                        ["cmd.exe", "/c", "start", "CodeLocal Cloud Backend", run_script],
                        shell=True,
                        cwd=self.codelocal_dir,
                    )
                    return True
            except Exception:
                pass

        # Fallback: run codelocal-cloud.exe directly
        exe_path = os.path.join(self.codelocal_dir, "codelocal-cloud.exe")
        if os.path.isfile(exe_path):
            try:
                env = os.environ.copy()
                env.setdefault("PORT", "3333")
                env.setdefault("HOST", "127.0.0.1")
                env.setdefault("PUBLIC_BASE_URL", "http://localhost:3333")
                env.setdefault("MCP_AUTH_SECRET", "localdevsecret123456789012345678901234")
                subprocess.Popen(
                    [exe_path],
                    env=env,
                    cwd=self.codelocal_dir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
                )
                return True
            except Exception:
                pass
        return False

    @staticmethod
    def generate_local_bearer_token(
        user_id: Optional[str] = None,
        secret_str: str = "localdevsecret123456789012345678901234",
        resource: str = "http://localhost:3333/mcp",
        valid_days: int = 365,
    ) -> str:
        """Generate a valid CodeLocal OAuth Access Token for local MCP authentication."""
        import base64
        import hashlib
        import hmac
        import time

        resolved_user = user_id or os.environ.get("CODELOCAL_USER_ID") or "usr_tk17112002"
        now = int(time.time())
        payload = {
            "typ": "access",
            "sub": resolved_user,
            "client_id": "tunnel-client",
            "resource": resource,
            "scope": "mcp:tools offline_access",
            "iat": now,
            "exp": now + valid_days * 24 * 3600,
            "jti": f"jti_tunnel_{int(time.time() * 1000)}",
            "sv": 1,
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        enc = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        secret_bytes = secret_str.encode("utf-8")
        sig = base64.urlsafe_b64encode(
            hmac.new(secret_bytes, enc.encode("ascii"), hashlib.sha256).digest()
        ).decode("ascii").rstrip("=")
        return enc + "." + sig
