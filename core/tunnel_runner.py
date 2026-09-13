import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple


class TunnelManager:
    """Manages the lifecycle, health supervision, and log redaction of Cloudflare and OpenAI MCP tunnels."""

    STATE_OFFLINE = "OFFLINE"
    STATE_STARTING = "STARTING"
    STATE_ACTIVE = "ACTIVE"
    STATE_RECONNECTING = "RECONNECTING"
    STATE_ERROR = "ERROR"

    MAX_LOG_BYTES = 2 * 1024 * 1024  # 2 MB rotation

    def __init__(
        self,
        base_dir: Optional[str] = None,
        status_callback: Optional[Callable[[str, str, str], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
    ):
        if not base_dir:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        else:
            self.base_dir = base_dir

        self.bin_dir = os.path.join(self.base_dir, "bin")
        self.runtime_dir = os.path.join(self.base_dir, "runtime")
        os.makedirs(self.bin_dir, exist_ok=True)
        os.makedirs(self.runtime_dir, exist_ok=True)

        self.cloudflared_bin = os.path.join(self.bin_dir, "cloudflared.exe")
        self.tunnel_client_bin = os.path.join(self.bin_dir, "tunnel-client.exe")
        self.log_file_path = os.path.join(self.runtime_dir, "tunnel_activity.log")
        self.health_url_file = os.path.join(self.runtime_dir, "openai_health.url")
        self.pid_file = os.path.join(self.runtime_dir, "tunnel.pid")

        self.status_callback = status_callback or (lambda state, url, msg: None)
        self.log_callback = log_callback or (lambda lvl, text: None)

        self.current_state = self.STATE_OFFLINE
        self.status_message = ""
        self.public_url = ""
        self.admin_ui_url = ""
        self.active_mode = ""  # "cloudflare" or "openai"
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.started_at: Optional[float] = None

        self._lock = threading.RLock()
        self._fatal_error = False
        self._supervisor_thread: Optional[threading.Thread] = None
        self._recent_logs: Deque[Tuple[str, str]] = deque(maxlen=300)

        # Store secrets currently active so they are redacted from all logs
        self._active_secrets: List[str] = []
        self._last_cf_params: Dict[str, Any] = {}
        self._last_oa_params: Dict[str, Any] = {}

    # -------------------------------------------------------------------------
    # Binary Verification
    # -------------------------------------------------------------------------
    def check_binaries(self) -> Dict[str, Dict[str, Any]]:
        """Verify presence and version of bundled binaries."""
        res = {
            "cloudflared": {"found": False, "path": self.cloudflared_bin, "version": "Not found"},
            "tunnel_client": {"found": False, "path": self.tunnel_client_bin, "version": "Not found"},
        }
        if os.path.isfile(self.cloudflared_bin):
            res["cloudflared"]["found"] = True
            try:
                out = subprocess.check_output(
                    [self.cloudflared_bin, "--version"],
                    text=True,
                    timeout=3,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                m = re.search(r"version\s+([^\s]+)", out)
                res["cloudflared"]["version"] = m.group(1) if m else out.strip().split("\n")[0]
            except Exception as e:
                res["cloudflared"]["version"] = f"Error: {e}"

        if os.path.isfile(self.tunnel_client_bin):
            res["tunnel_client"]["found"] = True
            try:
                out = subprocess.check_output(
                    [self.tunnel_client_bin, "--version"],
                    text=True,
                    timeout=3,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                res["tunnel_client"]["version"] = out.strip().split("\n")[0]
            except Exception as e:
                res["tunnel_client"]["version"] = f"Error: {e}"

        return res

    # -------------------------------------------------------------------------
    # Logging & Redaction
    # -------------------------------------------------------------------------
    def log(self, level: str, text: str) -> None:
        safe_text = self._redact(text)
        self._recent_logs.append((level, safe_text))
        self._rotate_log()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as handle:
                handle.write(f"[{timestamp}] [{level.upper()}] {safe_text}\n")
        except OSError:
            pass
        self.log_callback(level, safe_text)

    def _redact(self, text: str) -> str:
        for secret in self._active_secrets:
            if secret and len(secret) > 4:
                text = text.replace(secret, "[REDACTED]")
        return text

    def _rotate_log(self) -> None:
        try:
            if os.path.isfile(self.log_file_path) and os.path.getsize(self.log_file_path) > self.MAX_LOG_BYTES:
                backup = self.log_file_path + ".1"
                if os.path.exists(backup):
                    os.remove(backup)
                os.replace(self.log_file_path, backup)
        except OSError:
            pass

    def _set_state(self, state: str, public_url: str = "", message: str = "") -> None:
        with self._lock:
            self.current_state = state
            if public_url:
                self.public_url = public_url
            if message:
                self.status_message = message
        self.status_callback(state, self.public_url, self.status_message)

    # -------------------------------------------------------------------------
    # Cloudflare Tunnel Execution
    # -------------------------------------------------------------------------
    def start_cloudflare_tunnel(
        self,
        token: str,
        hostname: str,
        target_port: int = 3333,
        quick_tunnel: bool = False,
    ) -> bool:
        """Start Cloudflare Named Tunnel or Quick Tunnel."""
        with self._lock:
            if self.running:
                self.log("WARN", "A tunnel is already active. Stop it first.")
                return False

            if not os.path.isfile(self.cloudflared_bin):
                msg = f"cloudflared.exe not found at {self.cloudflared_bin}"
                self.log("ERROR", msg)
                self._set_state(self.STATE_ERROR, "", msg)
                return False

            token = token.strip()
            hostname = hostname.strip().lower()
            if hostname.startswith("https://"):
                hostname = hostname[8:]
            elif hostname.startswith("http://"):
                hostname = hostname[7:]
            hostname = hostname.split("/")[0].strip()

            if not quick_tunnel and not token:
                msg = "Cloudflare Named Tunnel requires a valid Tunnel Token."
                self.log("ERROR", msg)
                self._set_state(self.STATE_ERROR, "", msg)
                return False

            if not quick_tunnel and not hostname:
                msg = "Cloudflare Named Tunnel requires a configured Hostname."
                self.log("ERROR", msg)
                self._set_state(self.STATE_ERROR, "", msg)
                return False

            self.active_mode = "cloudflare"
            self._fatal_error = False
            self.admin_ui_url = ""
            self._last_cf_params = {
                "token": token,
                "hostname": hostname,
                "target_port": target_port,
                "quick_tunnel": quick_tunnel,
            }
            self._active_secrets = [token] if token else []
            self.running = True
            self.started_at = time.time()
            if quick_tunnel:
                self.public_url = ""
            else:
                self.public_url = f"https://{hostname}/mcp"

            started_msg = "Starting Cloudflare tunnel..."
            self._set_state(self.STATE_STARTING, self.public_url, started_msg)
            self.log("SYSTEM", f"Starting Cloudflare tunnel for local port {target_port} (Quick={quick_tunnel})...")

            spawned = self._spawn_cf_process()
            if not spawned:
                self.running = False
                return False

            self._supervisor_thread = threading.Thread(target=self._supervise_cf, daemon=True)
            self._supervisor_thread.start()
            return True

    def _spawn_cf_process(self) -> bool:
        """Internal helper to spawn the cloudflared process."""
        token = self._last_cf_params.get("token", "")
        target_port = self._last_cf_params.get("target_port", 3333)
        quick_tunnel = self._last_cf_params.get("quick_tunnel", False)

        if quick_tunnel:
            cmd = [
                self.cloudflared_bin,
                "tunnel",
                "--no-autoupdate",
                "--url",
                f"http://127.0.0.1:{target_port}",
            ]
            env = os.environ.copy()
        else:
            cmd = [
                self.cloudflared_bin,
                "tunnel",
                "--no-autoupdate",
                "run",
                "--token",
                token,
                "--url",
                f"http://127.0.0.1:{target_port}",
            ]
            env = os.environ.copy()
            env["TUNNEL_TOKEN"] = token

        try:
            flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            with self._lock:
                if not self.running:
                    return False
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=env,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=flags,
                )
            threading.Thread(target=self._read_cf_output, daemon=True).start()
            return True
        except Exception as e:
            self.log("ERROR", f"Failed to spawn cloudflared process: {e}")
            self._set_state(self.STATE_ERROR, "", str(e))
            return False

    def _read_cf_output(self) -> None:
        p = self.process
        if not p or not p.stdout:
            return

        quick_url_pattern = re.compile(r"https://[A-Za-z0-9.-]+\.trycloudflare\.com")
        for raw_line in iter(p.stdout.readline, ""):
            if not self.running and p.poll() is not None:
                break
            line = raw_line.strip()
            if not line:
                continue

            self.log("CLOUDFLARE", line)
            lower = line.lower()

            # Fatal error detection
            if (
                "provided tunnel token is not valid" in lower
                or "invalid tunnel token" in lower
                or "cannot determine default configuration path" in lower
                or 'error="unauthorized"' in lower
                or "unauthorized: invalid token" in lower
            ):
                self._fatal_error = True
                err_msg = "Token Cloudflare không hợp lệ hoặc đã hết hạn"
                self.log("ERROR", f"Fatal Cloudflare error: {err_msg}")
                self._set_state(self.STATE_ERROR, "", err_msg)
                # Terminate failing process to avoid hanging
                try:
                    if sys.platform == "win32" and p.pid:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                            capture_output=True,
                            check=False,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                    else:
                        p.terminate()
                except Exception:
                    pass
                break

            # Detect quick tunnel URL
            match = quick_url_pattern.search(line)
            if match:
                base = match.group(0)
                full_mcp = f"{base}/mcp"
                self.public_url = full_mcp
                self.log("SUCCESS", f"Quick Tunnel online! MCP Endpoint: {full_mcp}")
                self._set_state(self.STATE_ACTIVE, full_mcp, "Cloudflare Quick Tunnel Online")

            # Detect named tunnel connected
            if (
                "registered tunnel connection" in lower
                or "connection ... is connected" in lower
                or "connindex=0" in lower
                or "registered connindex=" in lower
                or "infra icmp proxy" in lower
            ):
                if not self.public_url and self._last_cf_params.get("hostname"):
                    self.public_url = f"https://{self._last_cf_params['hostname']}/mcp"
                self.log("SUCCESS", f"Cloudflare Named Tunnel is active: {self.public_url}")
                self._set_state(self.STATE_ACTIVE, self.public_url, "Cloudflare Tunnel Online")

        try:
            p.stdout.close()
        except Exception:
            pass

    def _supervise_cf(self) -> None:
        failures = 0
        while self.running:
            time.sleep(1)
            if not self.running or self._fatal_error:
                break
            if self.process and self.process.poll() is not None:
                code = self.process.returncode
                self.process = None
                if not self.running or self._fatal_error:
                    break
                failures += 1
                if failures >= 8:
                    msg = f"Cloudflare thoát liên tục (Code {code}). Dừng thử lại."
                    self.log("ERROR", msg)
                    self._set_state(self.STATE_ERROR, "", msg)
                    self.running = False
                    break

                delay = min(2 ** min(failures, 4), 20)
                self.log("WARN", f"cloudflared exited with code {code}; restarting in {delay}s (attempt {failures}/8)...")
                self._set_state(self.STATE_RECONNECTING, self.public_url, f"Reconnecting in {delay}s...")

                # Interruptible sleep
                for _ in range(delay * 2):
                    if not self.running or self._fatal_error:
                        break
                    time.sleep(0.5)

                if self.running and not self._fatal_error:
                    self._spawn_cf_process()

    # -------------------------------------------------------------------------
    # OpenAI Secure MCP Tunnel Execution
    # -------------------------------------------------------------------------
    def start_openai_tunnel(
        self,
        tunnel_id: str,
        runtime_api_key: str,
        bearer_token: str = "",
        alias: str = "codelocal-chatgpt",
        local_mcp_url: str = "http://127.0.0.1:3333/mcp",
    ) -> bool:
        """Start OpenAI Secure MCP Tunnel via tunnel-client.exe."""
        with self._lock:
            if self.running:
                self.log("WARN", "A tunnel is already active. Stop it first.")
                return False

            if not os.path.isfile(self.tunnel_client_bin):
                msg = f"tunnel-client.exe not found at {self.tunnel_client_bin}"
                self.log("ERROR", msg)
                self._set_state(self.STATE_ERROR, "", msg)
                return False

            tunnel_id = tunnel_id.strip().lower()
            runtime_api_key = runtime_api_key.strip()
            bearer_token = bearer_token.strip()
            alias = alias.strip() or "codelocal-chatgpt"
            local_mcp_url = local_mcp_url.strip() or "http://127.0.0.1:3333/mcp"

            if not re.fullmatch(r"tunnel_[0-9a-f]{32}", tunnel_id):
                msg = "Invalid OpenAI Tunnel ID. Must be 'tunnel_' followed by 32 lowercase hex characters."
                self.log("ERROR", msg)
                self._set_state(self.STATE_ERROR, "", "Tunnel ID phải là 'tunnel_' + 32 ký tự hex")
                return False

            if not runtime_api_key:
                msg = "OpenAI Runtime API Key is required."
                self.log("ERROR", msg)
                self._set_state(self.STATE_ERROR, "", "Thiếu OpenAI Runtime API Key")
                return False

            # Clean stale health url file
            if os.path.isfile(self.health_url_file):
                try:
                    os.remove(self.health_url_file)
                except OSError:
                    pass

            self.active_mode = "openai"
            self._fatal_error = False
            self.admin_ui_url = ""
            self._last_oa_params = {
                "tunnel_id": tunnel_id,
                "runtime_api_key": runtime_api_key,
                "bearer_token": bearer_token,
                "alias": alias,
                "local_mcp_url": local_mcp_url,
            }
            secrets = [runtime_api_key]
            if bearer_token:
                secrets.append(bearer_token)
            self._active_secrets = secrets
            self.running = True
            self.started_at = time.time()
            self.public_url = f"tunnel://{tunnel_id}"

            self._set_state(self.STATE_STARTING, self.public_url, "Connecting OpenAI Secure Tunnel...")
            has_bearer_msg = " [có kèm CodeLocal Bearer Token]" if bearer_token else ""
            self.log("SYSTEM", f"Connecting OpenAI Secure MCP Tunnel {tunnel_id} to local MCP ({local_mcp_url}){has_bearer_msg}...")

            spawned = self._spawn_oa_process()
            if not spawned:
                self.running = False
                return False

            self._supervisor_thread = threading.Thread(target=self._supervise_oa, daemon=True)
            self._supervisor_thread.start()
            return True

    def _spawn_oa_process(self) -> bool:
        """Internal helper to spawn tunnel-client daemon."""
        tunnel_id = self._last_oa_params.get("tunnel_id", "")
        runtime_api_key = self._last_oa_params.get("runtime_api_key", "")
        bearer_token = self._last_oa_params.get("bearer_token", "")
        local_mcp_url = self._last_oa_params.get("local_mcp_url", "http://127.0.0.1:3333/mcp")

        cmd = [
            self.tunnel_client_bin,
            "run",
            "--control-plane.tunnel-id",
            tunnel_id,
            "--mcp.server-url",
            local_mcp_url,
            "--health.listen-addr",
            "127.0.0.1:0",
            "--health.url-file",
            self.health_url_file,
            "--pid.file",
            self.pid_file,
            "--log.format",
            "struct-text",
        ]

        if bearer_token:
            auth_header = f"Authorization: Bearer {bearer_token}"
            cmd.extend([
                "--mcp.extra-headers",
                auth_header,
                "--mcp.discovery-extra-headers",
                auth_header,
            ])

        env = os.environ.copy()
        env["CONTROL_PLANE_API_KEY"] = runtime_api_key
        env["OPENAI_API_KEY"] = runtime_api_key
        env["M1_OPENAI_RUNTIME_KEY"] = runtime_api_key
        if bearer_token:
            env["MCP_EXTRA_HEADERS"] = f"Authorization: Bearer {bearer_token}"
            env["MCP_DISCOVERY_EXTRA_HEADERS"] = f"Authorization: Bearer {bearer_token}"

        try:
            flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            with self._lock:
                if not self.running:
                    return False
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=env,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=flags,
                )
            threading.Thread(target=self._read_oa_output, daemon=True).start()
            return True
        except Exception as e:
            self.log("ERROR", f"Failed to spawn tunnel-client process: {e}")
            self._set_state(self.STATE_ERROR, "", str(e))
            return False

    def _read_oa_output(self) -> None:
        p = self.process
        if not p or not p.stdout:
            return

        ui_pattern = re.compile(r"WEB UI:\s*(https?://[^\s]+/ui)")
        ui_param_pattern = re.compile(r"ui_url=(https?://[^\s]+)")

        for raw_line in iter(p.stdout.readline, ""):
            if not self.running and p.poll() is not None:
                break
            line = raw_line.strip()
            if not line:
                continue

            self.log("TUNNEL-CLIENT", line)
            lower = line.lower()

            # Parse embedded Web UI URL
            m_ui = ui_pattern.search(line) or ui_param_pattern.search(line)
            if m_ui:
                self.admin_ui_url = m_ui.group(1).rstrip('"').rstrip("'")
                self.log("SUCCESS", f"Tunnel-Client Web UI available: {self.admin_ui_url}")

            # Upstream MCP response handling (From CodeLocal to tunnel-client)
            if "failure_source=target_http" in lower or "upstream_status=" in lower or "mcp upstream error" in lower:
                if "status_code=401" in lower or "upstream_status=401" in lower:
                    self.log(
                        "WARN",
                        "CodeLocal Backend phản hồi HTTP 401 Unauthorized (yêu cầu xác thực OAuth). Tunnel vẫn đang kết nối bình thường với ChatGPT."
                    )
                continue

            # Fatal error detection from OpenAI Control Plane (Authentication rejection, invalid key/tunnel)
            is_control_plane_401 = (
                ("poll failed" in lower and "401" in lower)
                or ("component=control-plane" in lower and "401" in lower)
                or ('status="401 unauthorized"' in lower and "failure_source=target_http" not in lower)
                or ("failed to authenticate to control plane" in lower)
            )
            if is_control_plane_401:
                self._fatal_error = True
                err_msg = "401 Unauthorized: OpenAI Runtime API Key hoặc Tunnel ID không hợp lệ trên OpenAI Control Plane!"
                self.log("ERROR", err_msg)
                self._set_state(self.STATE_ERROR, self.public_url, err_msg)
                try:
                    if sys.platform == "win32" and p.pid:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                            capture_output=True,
                            check=False,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                    else:
                        p.terminate()
                except Exception:
                    pass
                break

            if "control plane api key is required" in lower:
                self._fatal_error = True
                err_msg = "Thiếu OpenAI Runtime API Key"
                self.log("ERROR", err_msg)
                self._set_state(self.STATE_ERROR, self.public_url, err_msg)
                try:
                    p.terminate()
                except Exception:
                    pass
                break

            # Warnings for local MCP unreachable
            if "failed to connect to mcp" in lower or "actively refused it" in lower:
                self.log("WARN", "CodeLocal Backend (Port 3333) chưa chạy hoặc từ chối kết nối!")

            # Positive active connection indicators
            if not self._fatal_error:
                if (
                    'msg="🟢 tunnel-client started"' in line
                    or "poller started" in lower
                    or "starting control-plane poller" in lower
                ):
                    self.log("SUCCESS", f"OpenAI Secure Tunnel is active: {self.public_url}")
                    self._set_state(self.STATE_ACTIVE, self.public_url, "OpenAI Secure Tunnel Online")

        try:
            p.stdout.close()
        except Exception:
            pass

    def _supervise_oa(self) -> None:
        failures = 0
        while self.running:
            time.sleep(1)
            if not self.running or self._fatal_error:
                break
            if self.process and self.process.poll() is not None:
                code = self.process.returncode
                self.process = None
                if not self.running or self._fatal_error:
                    break
                failures += 1
                if failures >= 8:
                    msg = f"tunnel-client thoát liên tục (Code {code}). Dừng thử lại."
                    self.log("ERROR", msg)
                    self._set_state(self.STATE_ERROR, "", msg)
                    self.running = False
                    break

                delay = min(2 ** min(failures, 4), 20)
                self.log("WARN", f"tunnel-client exited with code {code}; retrying in {delay}s (attempt {failures}/8)...")
                self._set_state(self.STATE_RECONNECTING, self.public_url, f"Reconnecting in {delay}s...")

                # Interruptible sleep
                for _ in range(delay * 2):
                    if not self.running or self._fatal_error:
                        break
                    time.sleep(0.5)

                if self.running and not self._fatal_error:
                    self._spawn_oa_process()

    # -------------------------------------------------------------------------
    # Stopping & Teardown
    # -------------------------------------------------------------------------
    def stop(self) -> None:
        """Stop the currently active tunnel."""
        with self._lock:
            self.running = False
            self._fatal_error = False

        self.log("SYSTEM", "Stopping tunnel process...")
        if self.process:
            pid = self.process.pid
            try:
                if sys.platform == "win32" and pid:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                        check=False,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self.process.terminate()
            except Exception:
                pass
            self.process = None

        # Clean PID file and health url file if present
        for path in (self.pid_file, self.health_url_file):
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

        self._active_secrets = []
        self.public_url = ""
        self.admin_ui_url = ""
        self.started_at = None
        self._set_state(self.STATE_OFFLINE, "", "Tunnel stopped")
        self.log("SYSTEM", "==================== TUNNEL STOPPED ====================")

    def get_uptime_str(self) -> str:
        """Return formatted uptime if running."""
        if not self.running or not self.started_at:
            return "--:--:--"
        elapsed = int(time.time() - self.started_at)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # -------------------------------------------------------------------------
    # Diagnostics (Doctor)
    # -------------------------------------------------------------------------
    def run_doctor(self, tunnel_id: str = "", api_key: str = "", mcp_url: str = "http://127.0.0.1:3333/mcp") -> List[str]:
        """Run deep diagnostics returning lines of diagnostic logs."""
        report = []
        report.append("=== KIỂM TRA CHẨN ĐOÁN HỆ THỐNG (DOCTOR) ===")

        # 1. Binary checks
        bins = self.check_binaries()
        for name, b in bins.items():
            st = "PASS" if b["found"] else "FAIL"
            report.append(f"[{st}] Binary {name}: {b['version']} ({b['path']})")

        # 2. OpenAI tunnel-client doctor
        if bins["tunnel_client"]["found"]:
            tid = tunnel_id if re.fullmatch(r"tunnel_[0-9a-f]{32}", tunnel_id) else "tunnel_0123456789abcdef0123456789abcdef"
            cmd = [
                self.tunnel_client_bin,
                "doctor",
                "--control-plane.tunnel-id",
                tid,
                "--mcp.server-url",
                mcp_url,
            ]
            env = os.environ.copy()
            if api_key:
                env["CONTROL_PLANE_API_KEY"] = api_key
            try:
                out = subprocess.check_output(
                    cmd,
                    env=env,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                report.append("--- OpenAI Tunnel Doctor Results ---")
                for line in out.splitlines():
                    if line.startswith("CHECK"):
                        report.append(f"  {line}")
            except subprocess.CalledProcessError as err:
                report.append("--- OpenAI Tunnel Doctor Results ---")
                for line in err.output.splitlines():
                    if line.startswith("CHECK") or line.startswith("RESULT"):
                        report.append(f"  {line}")
            except Exception as e:
                report.append(f"[WARN] Could not run tunnel-client doctor: {e}")

        report.append("=== KẾT THÚC CHẨN ĐOÁN ===")
        return report
