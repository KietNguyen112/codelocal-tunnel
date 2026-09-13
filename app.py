"""
CodeLocal Tunnel Gateway - Application Entry Point
"""

import os
import sys

# Ensure tunnel root is on PYTHONPATH
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Force UTF-8 on Windows console to support Vietnamese characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from ui.main_window import MainWindow


def main():
    # If headless / doctor argument passed
    if len(sys.argv) > 1 and sys.argv[1] in ("--doctor", "-d"):
        from core.tunnel_runner import TunnelManager
        from core.codelocal_client import CodeLocalDetector
        from core.config_store import ConfigManager

        cfg = ConfigManager()
        tid = cfg.get_openai_tunnel_id()
        key = cfg.get_openai_runtime_api_key()
        mcp_url = cfg.get_openai_local_mcp_url()

        mgr = TunnelManager()
        doc_lines = mgr.run_doctor(tunnel_id=tid, api_key=key, mcp_url=mcp_url)
        for line in doc_lines:
            print(line)

        det = CodeLocalDetector()
        res = det.check_all()
        print(f"CodeLocal Backend (3333): {'ONLINE' if res['backend_running'] else 'OFFLINE'}")
        print(f"CodeLocal Web UI (3000):  {'ONLINE' if res['web_running'] else 'OFFLINE'}")
        print(f"MCP Target URL:           {res['mcp_url']}")
        return

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
