# CodeLocal Tunnel Gateway

> **Ngôn ngữ**: **Tiếng Việt** | [English](README_EN.md)

Ứng dụng Desktop quản lý và khởi chạy tunnel kết nối ra ngoài Internet cho **CodeLocal Universal MCP** (hoặc bất kỳ MCP server cục bộ nào), phục vụ các nền tảng AI như **ChatGPT Web, Claude, Codex**.

Hỗ trợ 2 phương thức tunnel:
1. **Cloudflare Named Tunnel** (`cloudflared.exe`): Mở tunnel qua Cloudflare Zero Trust bằng Token và Public Hostname.
2. **OpenAI Secure MCP Tunnel** (`tunnel-client.exe`): Kết nối trực tiếp với OpenAI Control Plane / ChatGPT Connectors bằng Tunnel ID và Runtime API Key.

---

## 🎯 Tính năng chính

- **Quản lý đa phương thức Tunnel**:
  - Hỗ trợ cả Cloudflare Tunnel và OpenAI Secure Tunnel trong một ứng dụng duy nhất.
  - Tự động phát hiện và kiểm tra binary `cloudflared.exe` và `tunnel-client.exe` trong thư mục `bin/`.
- **Tích hợp CodeLocal**:
  - Tự động kiểm tra trạng thái hoạt động của CodeLocal Backend (Port 3333) và Web UI (Port 3000).
  - Tích hợp tính năng tạo nhanh CodeLocal Bearer Token để xác thực OAuth cục bộ cho MCP tools.
- **Bảo mật**:
  - Mã hóa Token và API Key bằng **Windows DPAPI** (`win32crypt`) khi lưu cấu hình trên máy.
  - Tự động ẩn (redact) các thông tin nhạy cảm trong log.
- **Giám sát & Tự phục hồi (Process Supervisor)**:
  - Giám sát tiến trình tunnel chạy nền; tự động kết nối lại khi đứt kết nối.
  - Quản lý PID và tự động dừng tiến trình con khi tắt ứng dụng, tránh xung đột cổng.
- **Console & Diagnostics**:
  - Stream log thời gian thực từ tiến trình tunnel.
  - Hỗ trợ chế độ chẩn đoán nhanh qua CLI (`--doctor`).
  - Hỗ trợ đa ngôn ngữ (Tiếng Việt / English).

---

## 📁 Cấu trúc thư mục

```text
tunnel/
├── bin/
│   ├── README.md             # Hướng dẫn tải & đặt binary cloudflared / tunnel-client
│   ├── cloudflared.exe       # Cloudflare Tunnel executable (tự tải vào)
│   └── tunnel-client.exe     # OpenAI Secure Tunnel executable (tự tải vào)
├── core/
│   ├── codelocal_client.py   # Kiểm tra trạng thái CodeLocal & sinh token MCP
│   ├── config_store.py       # Lưu trữ cấu hình & mã hóa Windows DPAPI
│   └── tunnel_runner.py      # Quản lý vòng đời và giám sát tiến trình tunnel
├── ui/
│   ├── components.py         # Các thành phần giao diện (Card, Badge, Input...)
│   ├── theme.py              # Định nghĩa màu sắc & từ điển ngôn ngữ (vi/en)
│   └── main_window.py        # Cửa sổ ứng dụng chính
├── runtime/
│   └── config.example.json   # Cấu hình mẫu (config thực tế và log được .gitignore)
├── tests/                    # Bộ kiểm thử tự động (22 unit tests)
├── app.py                    # Entry point ứng dụng (GUI & CLI)
├── run.bat                   # Script chạy nhanh 1-click trên Windows
├── requirements.txt          # Thư viện phụ thuộc (customtkinter)
├── README.md                 # Tài liệu Tiếng Việt
├── README_EN.md              # Tài liệu Tiếng Anh
└── .gitignore                # Chặn binary, token và log khỏi git
```

---

## 🛠️ Cài đặt & Khởi chạy

### Yêu cầu
- Windows 10/11
- Python 3.9 trở lên
- Đặt các file thực thi cần thiết vào thư mục `bin/` (xem chi tiết tại [`bin/README.md`](bin/README.md)).

### Cách 1: Chạy bằng file Batch
Nhấp đúp chuột vào file:
```cmd
run.bat
```
Script sẽ tự kiểm tra môi trường Python, cài đặt thư viện thiếu (`requirements.txt`) và mở ứng dụng.

### Cách 2: Chạy bằng dòng lệnh
```bash
cd tunnel
pip install -r requirements.txt
python app.py
```

### Chế độ kiểm tra chẩn đoán (CLI Doctor):
```bash
python app.py --doctor
```

---

## 📖 Hướng dẫn cấu hình

### 1. Cloudflare Named Tunnel (`cloudflared.exe`)

Dùng khi bạn có tên miền riêng trên Cloudflare và muốn có URL public cố định:

1. **Chuẩn bị trên Cloudflare Zero Trust**:
   - Truy cập **Zero Trust Dashboard** > **Networks** > **Tunnels** > Tạo Tunnel mới.
   - Chọn môi trường **Windows** và copy chuỗi **Token**.
   - Thêm **Public Hostname** trỏ về dịch vụ cục bộ:
     - **Service Type**: `HTTP`
     - **URL**: `localhost:3333` (hoặc cổng backend bạn sử dụng).
2. **Cấu hình trên ứng dụng**:
   - Chọn tab **Cloudflare Tunnel**.
   - Dán **Token** và nhập **Public Hostname**.
   - Bấm **Khởi động Tunnel**.
   - Sao chép MCP URL (ví dụ: `https://mcp.yourdomain.com/mcp`) để sử dụng trong ChatGPT hoặc Claude.

---

### 2. OpenAI Secure MCP Tunnel (`tunnel-client.exe`)

Dùng để kết nối trực tiếp với ChatGPT Connectors / Developer Mode:

1. **Chuẩn bị trên OpenAI Platform**:
   - Truy cập [OpenAI Platform Settings - Tunnels](https://platform.openai.com/settings/organization/tunnels).
   - Tạo Tunnel mới để nhận **Tunnel ID** (dạng `tunnel_...`) và **Runtime API Key** (dạng `sk-mcp-...`).
2. **Cấu hình trên ứng dụng**:
   - Chọn tab **ChatGPT Secure Tunnel**.
   - Nhập **Tunnel ID** và **Runtime API Key**.
   - *(Tùy chọn)* Bấm **⚡ Tạo tự động** tại ô *CodeLocal Bearer Token* nếu kết nối tới CodeLocal Backend.
   - Bấm **Khởi động Tunnel**.
3. **Kết nối trên ChatGPT**:
   - Vào **ChatGPT Settings** > **Connectors** và thêm connector bằng Tunnel ID vừa tạo.

---

## 🧪 Kiểm thử

Chạy bộ kiểm thử tự động:
```bash
cd tunnel
python -m unittest discover -s tests -v
```
Toàn bộ 22 unit tests kiểm tra mã hóa DPAPI, phân tích log, quản lý tiến trình, xử lý lỗi upstream 401 và tính toàn vẹn đa ngôn ngữ.
