# CodeLocal Tunnel Gateway

> **Language**: [Tiếng Việt](README.md) | **English**

A modern, production-grade Desktop GUI application designed to configure and expose local Model Context Protocol (MCP) servers to external AI platforms including **ChatGPT Web, Claude, and Codex**.

Supports two primary tunneling backends:
1. **Cloudflare Named Tunnel** (`cloudflared.exe`): Exposes services through Cloudflare Zero Trust using your private Tunnel Token and Public Hostname.
2. **OpenAI Secure MCP Tunnel** (`tunnel-client.exe`): Directly bridges your local MCP server to OpenAI Control Plane / ChatGPT Connectors via Tunnel ID and Runtime API Key.

---

## 🚀 Key Features

- **Modern Product-Grade Dark Theme**: Clean interface inspired by leading developer tools (Linear, Supabase, Vercel) featuring the Cyber Slate color palette, rounded micro-interactions, and real-time state feedback.
- **Deep CodeLocal Integration**:
  - Automatically probes the health of CodeLocal Cloud Backend (Port 3333) and CodeLocal Web (Port 3000).
  - Built-in **"▶ Start Backend"** action to spin up local services directly from the app.
- **Enterprise-Grade Security**:
  - Encrypts all Tokens and API Keys at rest using **Windows DPAPI** (`win32crypt`) with base64 obfuscation fallback on non-Windows platforms.
  - Automatically sanitizes and redacts sensitive credentials from activity logs.
- **Self-Healing Process Supervisor**:
  - Monitors background tunnel worker threads; automatically detects connection drops and applies exponential backoff reconnection.
  - Clean process teardown ensures zero orphaned or zombie background processes on exit.
- **Interactive Live Console**:
  - Real-time color-coded terminal log stream (`[SYSTEM]`, `[CLOUDFLARE]`, `[TUNNEL-CLIENT]`, `[SUCCESS]`, `[ERROR]`).
  - 1-click Public MCP URL copy with animated visual feedback.
  - Direct shortcut to open the ChatGPT Connectors management dashboard in your default browser.
- **Bilingual Support (i18n)**: Seamless instant switching between **Vietnamese** and **English**.

---

## 📁 Directory Structure

```text
tunnel/
├── bin/
│   ├── README.md             # Guide on obtaining cloudflared & tunnel-client
│   ├── cloudflared.exe       # Cloudflare Tunnel executable (downloaded separately)
│   └── tunnel-client.exe     # OpenAI Secure Tunnel executable (downloaded separately)
├── core/
│   ├── codelocal_client.py   # CodeLocal Backend/Web status probe & token helper
│   ├── config_store.py       # Configuration management & Windows DPAPI encryption
│   └── tunnel_runner.py      # Tunnel process lifecycle supervisor & health monitor
├── ui/
│   ├── components.py         # CustomTkinter reusable UI components
│   ├── theme.py              # Design system tokens, color palettes & i18n dictionaries
│   └── main_window.py        # Main application window & event bindings
├── runtime/
│   └── config.example.json   # Configuration template (actual config & logs are git-ignored)
├── tests/                    # Unit and integration test suite (22 tests)
├── app.py                    # Application entry point (CLI args & GUI runner)
├── run.bat                   # 1-click Windows quick launcher
├── requirements.txt          # Python dependencies (customtkinter)
├── README.md                 # Vietnamese documentation
├── README_EN.md              # English documentation
└── .gitignore                # Protects secrets, logs, and binaries from git commits
```

---

## 🛠️ Installation & Setup

### Prerequisites
- Windows 10/11 (or Linux/macOS for core headless mode)
- Python 3.9 or higher
- The required binary executables placed in `bin/` (see [`bin/README.md`](bin/README.md))

### Method 1: Quick Launcher (Windows)
Double-click the batch file:
```cmd
run.bat
```
This script checks for Python, automatically installs missing dependencies (`customtkinter`), and launches the application.

### Method 2: Manual Python Launch
```bash
cd tunnel
pip install -r requirements.txt
python app.py
```

### Headless Diagnostic / Doctor Mode
Run health and environment checks directly from the command line:
```bash
python app.py --doctor
```

---

## 📖 Configuration Guide

### 1. Cloudflare Named Tunnel (`cloudflared.exe`)

Best suited if you have your own domain name and need a stable, permanent public HTTPS endpoint (e.g., `https://mcp.yourdomain.com/mcp`).

1. **Cloudflare Zero Trust Setup**:
   - Navigate to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/) > **Networks** > **Tunnels**.
   - Create a new Tunnel (e.g., named `codelocal`).
   - Choose the **Windows** environment and copy the **Tunnel Token** (base64 string starting with `eyJhIjoi...`).
   - Under **Public Hostname**, configure your domain route:
     - **Subdomain / Domain**: e.g., `mcp` / `yourdomain.com` (Hostname: `mcp.yourdomain.com`)
     - **Service Type**: `HTTP`
     - **URL**: `localhost:3333`
2. **Configure in CodeLocal Tunnel App**:
   - Open the **☁️ Cloudflare Tunnel** tab.
   - Paste your **Token** into *Cloudflare Tunnel Token*.
   - Enter your **Hostname** into *Public Hostname*.
   - Select Target Service: *CodeLocal Backend (:3333)*.
   - Click **🚀 START TUNNEL**.
3. **Connect to ChatGPT / Claude**:
   - Your public MCP endpoint will be: `https://mcp.yourdomain.com/mcp`
   - Click **📋 Copy Public MCP URL** and paste it into your AI client.

---

### 2. OpenAI Secure MCP Tunnel (`tunnel-client.exe`)

Recommended when connecting directly to OpenAI ChatGPT Developer Mode / ChatGPT Connectors.

1. **OpenAI Platform Setup**:
   - Go to [OpenAI Platform Settings - Tunnels](https://platform.openai.com/settings/organization/tunnels).
   - Create a new Tunnel to receive your **Tunnel ID** (format `tunnel_` + 32 hex chars, e.g., `tunnel_3c8e41a9bf974bfa856e187f583e74a1`).
   - Generate a **Runtime API Key** (format `sk-mcp-...`).
2. **Configure in CodeLocal Tunnel App**:
   - Open the **🤖 ChatGPT Secure Tunnel** tab.
   - Enter your **OpenAI Tunnel ID** (input field validates the format with real-time green checkmark indicator).
   - Enter your **Runtime API Key**.
   - **CodeLocal Bearer Token (Optional)**: Click **⚡ Auto-Generate** to create a valid 365-day access token for your local CodeLocal instance. This token is automatically injected into all upstream requests to prevent HTTP 401 Unauthorized errors when ChatGPT invokes local MCP tools.
   - Set *Local MCP Server URL* (Default: `http://127.0.0.1:3333/mcp`).
   - Click **🚀 START TUNNEL**.
3. **Connect on ChatGPT Web**:
   - Click **🌐 Open ChatGPT Connectors** (or visit `https://chatgpt.com/#settings/Connectors`).
   - Add a new Connector using your Tunnel ID or `tunnel://<tunnel_id>`.

---

## 🧪 Running Tests

The test suite covers Windows DPAPI encryption, binary resolution, upstream HTTP 401 handling, bearer token generation, process lifecycle supervisors, and bilingual localization:

```bash
cd tunnel
python -m unittest discover -s tests -v
```

**Result**: 22/22 unit tests passing (100% success rate).

---

## 📄 License & Attribution

- Built for the **CodeLocal** developer ecosystem.
- Powered by [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), [Cloudflare Tunnel](https://github.com/cloudflare/cloudflared), and [OpenAI MCP](https://modelcontextprotocol.io/).
