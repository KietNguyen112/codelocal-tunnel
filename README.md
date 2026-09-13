# CodeLocal Tunnel Gateway

> **Ngôn ngữ**: **Tiếng Việt** | [English](README_EN.md)

Giao diện Desktop hiện đại, thiết kế chuẩn Product để thiết lập và mở tunnel kết nối ra ngoài mạng Internet cho **CodeLocal Universal MCP** phục vụ các ứng dụng AI như **ChatGPT Web, Claude, Codex**.

Hỗ trợ 2 phương thức mở tunnel chính với các binary được tích hợp sẵn trong thư mục `bin/`:
1. **Cloudflare Named Tunnel** (`cloudflared.exe`): Mở tunnel qua Cloudflare Zero Trust với Token và Public Hostname.
2. **OpenAI Secure MCP Tunnel** (`tunnel-client.exe`): Mở tunnel trực tiếp tới OpenAI Control Plane / ChatGPT Connectors với Tunnel ID và Runtime API Key.

---

## 🚀 Tính năng nổi bật

- **Giao diện chuẩn Product (Modern Dark Theme)**: Thiết kế giao diện lấy cảm hứng từ các công cụ devtools hàng đầu (Linear, Supabase, Vercel) với bảng màu Cyber Slate, hiệu ứng bo góc mượt mà, phản hồi trực quan.
- **Tích hợp sâu với CodeLocal**:
  - Tự động thăm dò trạng thái hoạt động của CodeLocal Cloud Backend (Port 3333) và CodeLocal Web (Port 3000).
  - Nút **"▶ Bật Backend"** tích hợp sẵn giúp khởi động CodeLocal trực tiếp từ ứng dụng nếu backend chưa chạy.
- **Bảo mật tối đa**:
  - Mã hóa toàn bộ Token và API Key bằng **Windows DPAPI** (`win32crypt`) khi lưu trên máy tính, không lưu plaintext.
  - Tự động ẩn (redact) các chuỗi nhạy cảm trong nhật ký hoạt động (Logs).
- **Cơ chế tự phục hồi (Self-Healing Supervisor)**:
  - Giám sát tiến trình tunnel chạy nền; tự động phát hiện lỗi ngắt kết nối và tự động kết nối lại (Exponential Backoff).
  - Dọn dẹp sạch sẽ tiến trình con khi tắt ứng dụng, không để lại zombie process.
- **Bảng điều khiển Console trực quan**:
  - Terminal hiển thị log thời gian thực với phân loại mã màu (`[SYSTEM]`, `[CLOUDFLARE]`, `[TUNNEL-CLIENT]`, `[SUCCESS]`, `[ERROR]`).
  - Nút sao chép URL 1-click với hiệu ứng phản hồi tức thì.
  - Mở trực tiếp trang quản lý ChatGPT Connectors trên trình duyệt.
- **Đa ngôn ngữ**: Hỗ trợ chuyển đổi nhanh giữa **Tiếng Việt** và **English**.

---

## 📁 Cấu trúc thư mục

```text
tunnel/
├── bin/
│   ├── README.md             # Hướng dẫn tải & cài đặt cloudflared & tunnel-client
│   ├── cloudflared.exe       # Cloudflare Tunnel binary (tự tải vào bin/)
│   └── tunnel-client.exe     # OpenAI Secure Tunnel binary (tự tải vào bin/)
├── core/
│   ├── codelocal_client.py   # Thăm dò & điều khiển CodeLocal Backend/Web
│   ├── config_store.py       # Quản lý cấu hình & mã hóa DPAPI
│   └── tunnel_runner.py      # Giám sát & khởi chạy tiến trình tunnel
├── ui/
│   ├── components.py         # Card, Status Badge, Password Toggle, Copy Field
│   ├── theme.py              # Bảng màu, typography & từ điển i18n
│   └── main_window.py        # Cửa sổ chính CustomTkinter
├── runtime/
│   └── config.example.json   # File cấu hình mẫu (config thực & logs được ignore)
├── tests/                    # Bộ kiểm thử Unit & Integration (22 tests)
├── app.py                    # Điểm khởi chạy ứng dụng (CLI + GUI)
├── run.bat                   # File kích hoạt nhanh 1-click trên Windows
├── requirements.txt          # Thư viện phụ thuộc (customtkinter)
└── .gitignore                # Chặn binary nặng, token cá nhân và logs
```

---

## 🛠️ Hướng dẫn cài đặt & Khởi chạy

### Cách 1: Khởi chạy nhanh bằng File Batch (Khuyên dùng)
Chỉ cần nhấp đúp chuột vào file:
```cmd
run.bat
```
File này sẽ tự kiểm tra môi trường Python, tự cài đặt thư viện cần thiết (`customtkinter`) nếu chưa có và mở giao diện ứng dụng.

### Cách 2: Khởi chạy bằng lệnh Python
```bash
cd tunnel
pip install -r requirements.txt
python app.py
```

### Chế độ kiểm tra chẩn đoán (Diagnostics / Doctor) qua dòng lệnh:
```bash
python app.py --doctor
```

---

## 📖 Hướng dẫn cấu hình chi tiết

### 1. Mở qua Cloudflare Tunnel (`cloudflared.exe`)

Phù hợp khi bạn sở hữu tên miền riêng và muốn có một URL cố định (vd: `https://mcp.yourdomain.com/mcp`).

1. **Chuẩn bị trên Cloudflare Zero Trust**:
   - Truy cập [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/) > **Networks** > **Tunnels**.
   - Tạo một Tunnel mới (vd đặt tên: `codelocal`).
   - Chọn môi trường **Windows** và copy chuỗi **Token** (chuỗi base64 dài bắt đầu bằng `eyJhIjoi...`).
   - Trong tab **Public Hostname**, thêm tên miền của bạn:
     - **Subdomain / Domain**: vd `mcp` / `yourdomain.com` (suy ra hostname: `mcp.yourdomain.com`)
     - **Service Type**: `HTTP`
     - **URL**: `localhost:3333`
2. **Cấu hình trên ứng dụng CodeLocal Tunnel**:
   - Chọn tab **☁️ Cloudflare Tunnel**.
   - Dán **Token** vào ô *Cloudflare Tunnel Token*.
   - Nhập **Hostname** vào ô *Public Hostname* (vd: `mcp.yourdomain.com`).
   - Chọn dịch vụ đích: *CodeLocal Backend (:3333)*.
   - Bấm **🚀 KHỞI ĐỘNG TUNNEL**.
3. **Sử dụng trên ChatGPT / MCP Client**:
   - MCP Endpoint của bạn sẽ là: `https://mcp.yourdomain.com/mcp`
   - Bấm nút **📋 Sao chép Public MCP URL** để dán vào ChatGPT hoặc Claude.

---

### 2. Mở qua ChatGPT Secure Tunnel (`tunnel-client.exe`)

Phù hợp khi bạn sử dụng tính năng Developer Mode / Connectors / Remote MCP chính thức của OpenAI ChatGPT.

1. **Chuẩn bị trên OpenAI Platform**:
   - Truy cập [OpenAI Platform Settings - Tunnels](https://platform.openai.com/settings/organization/tunnels).
   - Tạo một Tunnel mới. Bạn sẽ nhận được một **Tunnel ID** (dạng `tunnel_` + 32 ký tự hex, ví dụ: `tunnel_3c8e41a9bf974bfa856e187f583e74a1`).
   - Tạo hoặc lấy **Runtime API Key** (dạng `sk-mcp-...`).
2. **Cấu hình trên ứng dụng CodeLocal Tunnel**:
   - Chọn tab **🤖 ChatGPT Secure Tunnel**.
   - Nhập **OpenAI Tunnel ID** (ứng dụng sẽ tự kiểm tra định dạng và hiện dấu tích xanh khi hợp lệ).
   - Dán **Runtime API Key** vào ô tương ứng.
   - **CodeLocal Bearer Token (Tùy chọn)**: Bấm nút **⚡ Tạo tự động** để ứng dụng tự sinh token bản quyền cho tài khoản cục bộ của CodeLocal (có hiệu lực 365 ngày). Token này sẽ được tự động đính kèm vào mọi request tới CodeLocal Backend (Port 3333), giúp ChatGPT gọi thẳng vào toàn bộ 14 MCP tools mà không bao giờ bị 401 Unauthorized.
   - Mục *Local MCP Server URL* để mặc định: `http://127.0.0.1:3333/mcp`.
   - Bấm **🚀 KHỞI ĐỘNG TUNNEL**.
3. **Kết nối trên ChatGPT**:
   - Bấm nút **🌐 Mở ChatGPT Connectors** (hoặc truy cập `https://chatgpt.com/#settings/Connectors`).
   - Thêm Connector mới và nhập Tunnel ID hoặc chuỗi `tunnel://<tunnel_id>`.

---

## 🧪 Kiểm thử (Testing)

Dự án bao gồm bộ unit test toàn diện kiểm tra bảo mật mã hóa DPAPI, nhận diện nhị phân, bộ phát hiện CodeLocal, chuẩn hóa định dạng ID, trích xuất Web UI inspector URL, xử lý lỗi upstream 401 không kill tunnel, sinh bearer token tự động, và kiểm thử tính toàn vẹn đa ngôn ngữ (i18n):

```bash
cd tunnel
python -m unittest discover -s tests -v
```

Kết quả: Toàn bộ 22 test case pass 100%.
