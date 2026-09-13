"""
Theme, styling constants and internationalization for CodeLocal Tunnel Desktop.
"""

# -----------------------------------------------------------------------------
# Color Palette (Modern Dark Cyber/SaaS Palette)
# -----------------------------------------------------------------------------
BG_DARK = "#111214"
BG_SURFACE = "#18191c"
BG_SURFACE_ALT = "#202126"
BG_INPUT = "#121316"
BG_TERMINAL = "#0d0e10"

BORDER_SUBTLE = "#2a2c31"
BORDER_FOCUS = "#5b8def"
BORDER_ACTIVE = "#7aa2f7"

ACCENT_CYAN = "#6f95e8"
ACCENT_CYAN_HOVER = "#5d82d3"
ACCENT_BLUE = "#4f76c9"
ACCENT_BLUE_HOVER = "#4265ae"

COLOR_ONLINE = "#48b47a"
COLOR_CONNECTING = "#d5a94b"
COLOR_OFFLINE = "#858992"
COLOR_ERROR = "#d95f63"

TEXT_PRIMARY = "#f1f2f4"
TEXT_SECONDARY = "#b0b3b9"
TEXT_MUTED = "#777b83"
TEXT_CYAN = "#91aeea"
TEXT_EMERALD = "#70c997"

# -----------------------------------------------------------------------------
# Internationalization (i18n)
# -----------------------------------------------------------------------------
I18N = {
    "vi": {
        "app_title": "CodeLocal Tunnel Gateway",
        "app_subtitle": "Cổng kết nối Tunnel an toàn cho MCP Web (ChatGPT, Claude, Codex)",
        "backend_online": "● CodeLocal Backend: Sẵn sàng (Port 3333)",
        "backend_offline": "○ CodeLocal Backend: Chưa chạy",
        "start_backend_btn": "▶ Bật Backend",
        "mode_cf": "Cloudflare Tunnel (Token + Hostname)",
        "mode_openai": "ChatGPT Secure Tunnel (Tunnel ID + API Key)",
        # Cloudflare fields
        "cf_title": "Cấu hình Cloudflare Named Tunnel",
        "cf_token_label": "Cloudflare Tunnel Token:",
        "cf_token_placeholder": "Nhập token (vd: eyJhIjoi...)",
        "cf_token_hint": "Lấy từ Cloudflare Zero Trust > Networks > Tunnels > Install Connector",
        "cf_host_label": "Public Hostname (Tên miền):",
        "cf_host_placeholder": "mcp.yourdomain.com",
        "cf_host_hint": "Tên miền đã cấu hình Public Hostname trỏ về http://localhost:3333",
        "cf_port_label": "Dịch vụ đích (Target Port):",
        "cf_port_backend": "CodeLocal Backend (:3333) [Khuyên dùng cho MCP]",
        "cf_port_web": "CodeLocal Web UI (:3000)",
        "cf_port_custom": "Cổng tùy chỉnh",
        "cf_custom_port_label": "Port:",
        "cf_quick_tunnel": "Sử dụng Quick Tunnel (trycloudflare - không cần token)",
        # OpenAI fields
        "oa_title": "Cấu hình OpenAI Secure MCP Tunnel",
        "oa_id_label": "OpenAI Tunnel ID:",
        "oa_id_placeholder": "tunnel_ + 32 ký tự hex (vd: tunnel_3c8e41a9bf974bfa856e187f583e74a1)",
        "oa_id_hint": "Lấy từ platform.openai.com > Settings > Tunnels hoặc ChatGPT Connectors",
        "oa_key_label": "OpenAI Runtime API Key:",
        "oa_key_placeholder": "sk-mcp-... hoặc API Key cấp quyền tunnel",
        "oa_key_hint": "Khóa xác thực OpenAI Control Plane (được mã hóa DPAPI an toàn)",
        "oa_bearer_label": "CodeLocal Bearer Token (Tùy chọn):",
        "oa_bearer_placeholder": "Dán Bearer token hoặc bấm '⚡ Tạo tự động'...",
        "oa_bearer_hint": "Đính kèm vào request để xác thực với CodeLocal Backend (Port 3333), bỏ qua 401",
        "btn_gen_bearer": "⚡ Tạo tự động",
        "oa_alias_label": "Runtime Alias:",
        "oa_alias_placeholder": "codelocal-chatgpt",
        "oa_local_mcp_label": "Local MCP Server URL:",
        "oa_local_mcp_placeholder": "http://127.0.0.1:3333/mcp",
        # Status & Controls
        "status_title": "Trạng thái kết nối",
        "btn_start": "🚀 KHỞI ĐỘNG TUNNEL",
        "btn_stop": "⏹ DỪNG TUNNEL",
        "btn_starting": "⏳ ĐANG KHỞI ĐỘNG...",
        "btn_stopping": "⏳ ĐANG DỪNG...",
        "copy_mcp_url": "📋 Sao chép Public MCP URL",
        "open_chatgpt_btn": "🌐 Mở ChatGPT Connectors",
        "open_admin_ui_btn": "📊 Mở Tunnel Web UI",
        "copied": "✓ Đã sao chép!",
        "status_offline": "● CHƯA KẾT NỐI",
        "status_starting": "● ĐANG KẾT NỐI...",
        "status_active": "● ĐANG HOẠT ĐỘNG (ONLINE)",
        "status_reconnecting": "● ĐANG KẾT NỐI LẠI...",
        "status_error": "● LỖI KẾT NỐI",
        "status_detail_offline": "Tunnel đang tắt. Chọn chế độ và nhấn Khởi động Tunnel để bắt đầu.",
        "status_detail_starting": "Đang kết nối tới máy chủ tunnel và thiết lập tuyến mạng...",
        "status_detail_active_cf": "Cloudflare Tunnel đang hoạt động. Sao chép URL bên dưới vào ChatGPT Connectors.",
        "status_detail_active_oa": "OpenAI Secure Tunnel đang hoạt động và kết nối trực tiếp với ChatGPT Control Plane.",
        "uptime": "Thời gian chạy:",
        # Log terminal
        "logs_title": "Nhật ký hoạt động (Terminal Console)",
        "btn_clear_log": "Xóa màn hình",
        "btn_open_log": "Mở file Log",
        "btn_auto_scroll": "Tự cuộn",
        "btn_doctor": "🩺 Kiểm tra Binaries & Mạng",
        # Guide
        "guide_title": "💡 Hướng dẫn cấu hình ChatGPT Web với CodeLocal MCP",
        "guide_text": "1. Mở ChatGPT > Cài đặt > Connectors (hoặc Developer Mode).\n2. Thêm MCP Server mới: Paste URL ở trên vào ô Server URL.\n3. Nếu dùng Cloudflare: Endpoint là https://<hostname>/mcp.\n4. Nếu dùng OpenAI Tunnel: Nhập Tunnel ID và kết nối trực tiếp.\n5. Đảm bảo CodeLocal Backend (Port 3333) đang chạy để nhận lệnh từ ChatGPT.",
        "lang_switch": "Ngôn ngữ / Language",
        # Error & alerts
        "err_unauthorized": "401 Unauthorized: OpenAI Runtime API Key hoặc Tunnel ID không hợp lệ!",
        "err_cf_token": "Token Cloudflare không hợp lệ hoặc đã hết hạn!",
        "err_backend_offline": "CodeLocal Backend (Port 3333) chưa chạy! Vui lòng bấm '▶ Bật Backend' trước.",
        "err_missing_token": "Vui lòng nhập Cloudflare Tunnel Token để mở tunnel!",
        "err_missing_host": "Vui lòng nhập Public Hostname đã gán trong Cloudflare!",
        "err_invalid_tid": "OpenAI Tunnel ID phải có định dạng 'tunnel_' + 32 ký tự hex thường!\n(Vd: tunnel_3c8e41a9bf974bfa856e187f583e74a1)",
        "err_missing_key": "Vui lòng nhập OpenAI Runtime API Key!",
        "warn_title": "Cảnh báo",
        "info_title": "Thông báo",
    },
    "en": {
        "app_title": "CodeLocal Tunnel Gateway",
        "app_subtitle": "Secure Remote MCP Tunnel for ChatGPT & AI Coding Clients",
        "backend_online": "● CodeLocal Backend: Online (Port 3333)",
        "backend_offline": "○ CodeLocal Backend: Offline",
        "start_backend_btn": "▶ Start Backend",
        "mode_cf": "Cloudflare Tunnel (Token + Hostname)",
        "mode_openai": "ChatGPT Secure Tunnel (Tunnel ID + API Key)",
        # Cloudflare fields
        "cf_title": "Cloudflare Named Tunnel Configuration",
        "cf_token_label": "Cloudflare Tunnel Token:",
        "cf_token_placeholder": "Paste token (e.g., eyJhIjoi...)",
        "cf_token_hint": "From Cloudflare Zero Trust > Networks > Tunnels > Install Connector",
        "cf_host_label": "Public Hostname (Domain):",
        "cf_host_placeholder": "mcp.yourdomain.com",
        "cf_host_hint": "Public Hostname routing to http://localhost:3333",
        "cf_port_label": "Target Service Port:",
        "cf_port_backend": "CodeLocal Backend (:3333) [Recommended for MCP]",
        "cf_port_web": "CodeLocal Web UI (:3000)",
        "cf_port_custom": "Custom Port",
        "cf_custom_port_label": "Port:",
        "cf_quick_tunnel": "Use Quick Tunnel (trycloudflare - no token required)",
        # OpenAI fields
        "oa_title": "OpenAI Secure MCP Tunnel Configuration",
        "oa_id_label": "OpenAI Tunnel ID:",
        "oa_id_placeholder": "tunnel_ + 32 hex chars (e.g. tunnel_3c8e41a9bf974bfa856e187f583e74a1)",
        "oa_id_hint": "From platform.openai.com > Settings > Tunnels or ChatGPT Connectors",
        "oa_key_label": "OpenAI Runtime API Key:",
        "oa_key_placeholder": "sk-mcp-... or Runtime API Key",
        "oa_key_hint": "OpenAI Control Plane API Key (securely encrypted via DPAPI)",
        "oa_bearer_label": "CodeLocal Bearer Token (Optional):",
        "oa_bearer_placeholder": "Paste Bearer token or click '⚡ Auto Generate'...",
        "oa_bearer_hint": "Injected into requests to authenticate with CodeLocal Backend (Port 3333), bypassing 401",
        "btn_gen_bearer": "⚡ Auto Generate",
        "oa_alias_label": "Runtime Alias:",
        "oa_alias_placeholder": "codelocal-chatgpt",
        "oa_local_mcp_label": "Local MCP Server URL:",
        "oa_local_mcp_placeholder": "http://127.0.0.1:3333/mcp",
        # Status & Controls
        "status_title": "Connection Status",
        "btn_start": "🚀 START TUNNEL",
        "btn_stop": "⏹ STOP TUNNEL",
        "btn_starting": "⏳ STARTING...",
        "btn_stopping": "⏳ STOPPING...",
        "copy_mcp_url": "📋 Copy Public MCP URL",
        "open_chatgpt_btn": "🌐 Open ChatGPT Connectors",
        "open_admin_ui_btn": "📊 Open Tunnel Web UI",
        "copied": "✓ Copied!",
        "status_offline": "● OFFLINE",
        "status_starting": "● CONNECTING...",
        "status_active": "● ACTIVE (ONLINE)",
        "status_reconnecting": "● RECONNECTING...",
        "status_error": "● CONNECTION ERROR",
        "status_detail_offline": "Tunnel is offline. Select mode and click Start Tunnel.",
        "status_detail_starting": "Connecting to tunnel edge and registering route...",
        "status_detail_active_cf": "Cloudflare Tunnel is active. Copy the URL below into ChatGPT Connectors.",
        "status_detail_active_oa": "OpenAI Secure Tunnel is active and connected to OpenAI Control Plane.",
        "uptime": "Uptime:",
        # Log terminal
        "logs_title": "Activity Logs (Terminal Console)",
        "btn_clear_log": "Clear Log",
        "btn_open_log": "Open Log File",
        "btn_auto_scroll": "Auto-scroll",
        "btn_doctor": "🩺 Run Diagnostics",
        # Guide
        "guide_title": "💡 How to Connect ChatGPT Web to CodeLocal MCP",
        "guide_text": "1. Open ChatGPT > Settings > Connectors (or Developer Mode).\n2. Add New MCP Server: Paste the Public URL above into Server URL.\n3. For Cloudflare: MCP Endpoint is https://<hostname>/mcp.\n4. For OpenAI Tunnel: Enter Tunnel ID and connect directly.\n5. Ensure CodeLocal Backend (Port 3333) is running to receive commands.",
        "lang_switch": "Language",
        # Error & alerts
        "err_unauthorized": "401 Unauthorized: Invalid OpenAI Runtime API Key or Tunnel ID!",
        "err_cf_token": "Invalid or expired Cloudflare Tunnel Token!",
        "err_backend_offline": "CodeLocal Backend (Port 3333) is offline! Please click '▶ Start Backend' first.",
        "err_missing_token": "Please enter Cloudflare Tunnel Token!",
        "err_missing_host": "Please enter the Public Hostname configured in Cloudflare!",
        "err_invalid_tid": "OpenAI Tunnel ID must match 'tunnel_' followed by 32 hex chars!\n(E.g. tunnel_3c8e41a9bf974bfa856e187f583e74a1)",
        "err_missing_key": "Please enter OpenAI Runtime API Key!",
        "warn_title": "Warning",
        "info_title": "Information",
    },
}
