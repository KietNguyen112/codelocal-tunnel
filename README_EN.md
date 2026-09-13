# CodeLocal Tunnel Gateway

> **Language**: [Tiếng Việt](README.md) | **English**

Desktop application to configure and run tunnels exposing **CodeLocal Universal MCP** (or any local MCP server) to external AI platforms including **ChatGPT Web, Claude, and Codex**.

Supports two tunneling backends:
1. **Cloudflare Named Tunnel** (`cloudflared.exe`): Exposes services through Cloudflare Zero Trust using a Tunnel Token and Public Hostname.
2. **OpenAI Secure MCP Tunnel** (`tunnel-client.exe`): Directly connects to OpenAI Control Plane / ChatGPT Connectors using a Tunnel ID and Runtime API Key.

---

## 🎯 Core Features

- **Multi-Backend Tunnel Management**:
  - Supports both Cloudflare Tunnel and OpenAI Secure Tunnel in one unified tool.
  - Automatically verifies executable presence in the `bin/` directory.
- **CodeLocal Integration**:
  - Automatically monitors CodeLocal Backend (Port 3333) and Web UI (Port 3000) health status.
  - Built-in 1-click CodeLocal Bearer Token generator for local OAuth authentication.
- **Security**:
  - Encrypts Tokens and API Keys on disk using **Windows DPAPI** (`win32crypt`).
  - Automatically redacts sensitive credentials from log outputs.
- **Process Supervisor & Self-Healing**:
  - Tracks background tunnel processes and automatically reconnects on dropped connections.
  - Tracks PID and performs clean shutdown on exit, preventing orphaned background processes.
- **Console & Diagnostics**:
  - Real-time stdout/stderr log streaming from tunnel processes.
  - CLI diagnostic check mode (`--doctor`).
  - Bilingual support (Vietnamese / English).

---

## 📁 Directory Structure

```text
tunnel/
├── bin/
│   ├── README.md             # Instructions for obtaining required binaries
│   ├── cloudflared.exe       # Cloudflare Tunnel executable (user-supplied)
│   └── tunnel-client.exe     # OpenAI Secure Tunnel executable (user-supplied)
├── core/
│   ├── codelocal_client.py   # CodeLocal status detection & token generation
│   ├── config_store.py       # Configuration management & Windows DPAPI encryption
│   └── tunnel_runner.py      # Tunnel lifecycle supervisor & process runner
├── ui/
│   ├── components.py         # Reusable UI components (Cards, Badges, Inputs)
│   ├── theme.py              # Color tokens & localization dictionaries (vi/en)
│   └── main_window.py        # Main application window
├── runtime/
│   └── config.example.json   # Template config (actual config & logs are git-ignored)
├── tests/                    # Unit and integration test suite (22 tests)
├── app.py                    # Application entry point (GUI & CLI)
├── run.bat                   # 1-click Windows batch launcher
├── requirements.txt          # Python dependencies (customtkinter)
├── README.md                 # Vietnamese documentation
├── README_EN.md              # English documentation
└── .gitignore                # Protects secrets, logs, and binaries from git
```

---

## 🛠️ Installation & Setup

### Prerequisites
- Windows 10/11
- Python 3.9 or higher
- Place required executables into `bin/` (see [`bin/README.md`](bin/README.md)).

### Method 1: Batch Launcher (Windows)
Double-click:
```cmd
run.bat
```
The script verifies Python, installs missing dependencies (`requirements.txt`), and launches the app.

### Method 2: Command Line
```bash
cd tunnel
pip install -r requirements.txt
python app.py
```

### CLI Doctor Mode
Run health and binary diagnostics from terminal:
```bash
python app.py --doctor
```

---

## 📖 Configuration Guide

### 1. Cloudflare Named Tunnel (`cloudflared.exe`)

For users with a custom domain on Cloudflare who need a persistent public HTTPS URL:

1. **Cloudflare Zero Trust Setup**:
   - Open **Zero Trust Dashboard** > **Networks** > **Tunnels** > Create Tunnel.
   - Choose **Windows** and copy your **Token**.
   - Add a **Public Hostname** routing to your local service:
     - **Service Type**: `HTTP`
     - **URL**: `localhost:3333` (or your target backend port).
2. **App Configuration**:
   - Open the **Cloudflare Tunnel** tab.
   - Paste **Token** and enter your **Public Hostname**.
   - Click **Start Tunnel**.
   - Copy the public MCP URL (e.g. `https://mcp.yourdomain.com/mcp`) for ChatGPT or Claude.

---

### 2. OpenAI Secure MCP Tunnel (`tunnel-client.exe`)

For connecting directly to ChatGPT Connectors / Developer Mode:

1. **OpenAI Platform Setup**:
   - Navigate to [OpenAI Platform Settings - Tunnels](https://platform.openai.com/settings/organization/tunnels).
   - Create a Tunnel to obtain your **Tunnel ID** (`tunnel_...`) and **Runtime API Key** (`sk-mcp-...`).
2. **App Configuration**:
   - Open the **ChatGPT Secure Tunnel** tab.
   - Enter your **Tunnel ID** and **Runtime API Key**.
   - *(Optional)* Click **⚡ Auto-Generate** for *CodeLocal Bearer Token* if bridging to CodeLocal Backend.
   - Click **Start Tunnel**.
3. **Connect on ChatGPT**:
   - Open **ChatGPT Settings** > **Connectors** and add a connector using the Tunnel ID.

---

## 🧪 Testing

Run automated tests:
```bash
cd tunnel
python -m unittest discover -s tests -v
```
All 22 unit tests verify DPAPI encryption, log parsing, process supervisors, upstream 401 handling, and localization.
