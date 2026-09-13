# Binaries Directory (`tunnel/bin/`)

Thư mục này chứa các file thực thi (binaries) của tunnel client. Các file thực thi `.exe` đã được cấu hình trong `.gitignore` để tránh đẩy file nhị phân nặng và vi phạm bản quyền lên Git.

---

## 1. Cloudflare Tunnel (`cloudflared.exe`)

- **Nguồn tải chính thức**: [Cloudflare GitHub Releases](https://github.com/cloudflare/cloudflared/releases)
- **Cách cài đặt**:
  1. Tải file `cloudflared-windows-amd64.exe` mới nhất.
  2. Đổi tên file thành `cloudflared.exe`.
  3. Đặt vào thư mục `tunnel/bin/`.

---

## 2. OpenAI ChatGPT Secure Tunnel (`tunnel-client.exe`)

- **Nguồn**: Được phát hành bởi OpenAI cho tính năng kết nối cục bộ của ChatGPT Desktop / Developer Mode MCP.
- **Cách cài đặt**:
  1. Lấy file thực thi `tunnel-client.exe` từ gói ChatGPT Desktop hoặc công cụ phát triển MCP của OpenAI.
  2. Đặt file vào thư mục `tunnel/bin/`.

---

> 💡 **Lưu ý**: Cả 2 file này cần được đặt trực tiếp trong thư mục `bin/` với đúng tên:
> - `bin/cloudflared.exe`
> - `bin/tunnel-client.exe`
