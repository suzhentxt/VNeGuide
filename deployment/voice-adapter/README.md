# VNeGuide voice adapter

Container này là ranh giới bảo mật giữa HTTPS public và Qwen ASR trong Docker network. Nó cung cấp
`POST /v1/audio/transcriptions`, bắt buộc Bearer token, kiểm tra MIME/kích thước/thời lượng thật bằng
`ffprobe`, chuẩn hóa audio thành WAV mono 16 kHz rồi mới chuyển tiếp tới Qwen.

Tạo secret **không có newline** bằng công cụ quản lý secret của VPS, bảo đảm file thuộc `root:root`,
mode `0440`; không đặt key trong Compose hoặc URL. Adapter fail closed nếu file được cấu hình nhưng
thiếu, rỗng hoặc chứa newline/NUL. Sau đó chạy Compose với các biến tối thiểu:

```text
VNEGUIDE_VOICE_ADAPTER_API_KEY_SOURCE=/opt/vneguide/shared/voice-adapter-api-key
VNEGUIDE_VOICE_ADAPTER_UPSTREAM_URL=http://vneguide-stt:9208/v1/audio/transcriptions
VNEGUIDE_TRANSLATOR_NETWORK=vn-en-translator_default
```

Trên VPS hiện tại, gắn container `vneguide-stt` vào external network `vn-en-translator_default` với
alias `vneguide-stt` trước khi khởi động adapter. Model thật đang phục vụ là
`Qwen/Qwen3-ASR-0.6B-hf`; `translator:8000` là dịch vụ dịch máy và không phải upstream ASR. Adapter và
STT giao tiếp trực tiếp trong Docker network; port STT thô phải bị chặn từ interface Internet.

```bash
sudo docker network connect --alias vneguide-stt vn-en-translator_default vneguide-stt
sudo install -o root -g root -m 0644 \
  deployment/voice-adapter/vneguide-stt-private.service \
  /etc/systemd/system/vneguide-stt-private.service
sudo systemctl daemon-reload
sudo systemctl enable --now vneguide-stt-private.service
```

Compose chạy app bằng UID `10001`, GID `0` để đọc file secret bind-mounted qua quyền group-read;
container vẫn non-root, drop toàn bộ capability và dùng filesystem read-only. Compose thường bỏ qua
`uid/gid/mode` của file secret ngoài Swarm, vì vậy không đổi file về `0400` nếu dùng deployment này.

Unit firewall chỉ chặn TCP/9208 đi vào từ `eth0`; nó không đổi các cổng 80/443/9000 và không chặn
traffic Docker nội bộ. Xác nhận tên public interface trước khi cài nếu dùng VPS khác.

Compose không publish host port. Cloudflare Tunnel/Caddy phải cùng external network và route hostname
HTTPS riêng tới `http://voice-adapter:9210`. Trên Vercel, đặt URL HTTPS đó làm STT base URL và đặt cùng
Bearer token trong server-side environment; không dùng biến `NEXT_PUBLIC_*` cho secret.
Validate Caddy trước khi reload; snippet mẫu nằm trong `Caddyfile.snippet.example`.
