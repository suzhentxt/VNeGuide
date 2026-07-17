# Nhật ký tiến độ VNeGuide

## Trạng thái hiện tại

- Phạm vi runtime được khóa bởi `data/README.md` và chỉ gồm `2.000635`, `1.013314`, `1.004194`.
- Domain/data foundation, structured extraction, deterministic rules, suggestion-aware core và CLI
  đã có source.
- AI hỗ trợ mock, OpenAI Responses và LiteLLM Chat Completions.
- HTTP Chat API cung cấp session TTL/capacity/lock, send, Accept/Reject/Edit và reset.
- `demoweb/` là Next.js frontend độc lập; BFF giữ session ID trong cookie `HttpOnly`.
- Nhánh `integration/release-dev` đang hợp nhất LiteLLM từ `dev` với FastAPI/Next.js từ `tuan`.
- Frontend Hôn nhân và gia đình là phạm vi cũ, không phải nguồn nghiệp vụ; phải thay bằng đúng ba
  thủ tục trước release.

## Ưu tiên release

1. Hoàn tất merge `dev` + `tuan` và đưa commit tài liệu phạm vi `709b795` vào nhánh tích hợp.
2. Cài dependency bằng `.[api,dev]` và `npm ci`, sau đó chạy lại toàn bộ Python/web gates.
3. Bổ sung E2E cho đúng ba thủ tục, out-of-scope, revision/reset/timeout và OCR fallback.
4. Deploy public frontend/backend, smoke `/health`, ghi metrics và chuẩn bị rollback/video.

## Bằng chứng đã có trước nhánh release

- Core/rules + LiteLLM: Ruff/format/Mypy pass; Pytest `87 passed, 1 skipped`; coverage `80.82%`.
- Provider-only smoke đã gọi `Qwen/Qwen3.5-9B` bằng dữ liệu tổng hợp và nhận structured output.
- Web/API trên nhánh `tuan`: Ruff/Mypy pass; Pytest `79 passed, 1 skipped`; coverage `82.32%`.
- `demoweb` trên nhánh `tuan`: ESLint, TypeScript và production build pass; local smoke
  web → BFF → Python API pass bằng mock provider.

Các số liệu trên là bằng chứng lịch sử của từng nhánh. Trạng thái hợp nhất chỉ được công bố sau khi
quality gate được chạy lại trên `integration/release-dev`.

## Nhật ký phiên

### 2026-07-18 — Release integration đang thực hiện

- Tạo `integration/release-dev` từ `dev`.
- Merge `tuan`; source LiteLLM, FastAPI và Next.js hợp nhất tự động, conflict chỉ nằm trong cấu hình
  mẫu và tài liệu vận hành.
- Giữ cả cấu hình LiteLLM lẫn HTTP API trong `.env.example`.
- Chưa công bố release hoàn thành, public URL hoặc metric mới cho tới khi full gate và deploy pass.

### 2026-07-18 — HTTP API và demoweb trên nhánh nguồn

- Thêm FastAPI session adapter và Next.js BFF/chatbox với cookie `HttpOnly`.
- Chatbox có Accept/Sửa/Từ chối, validation, nguồn, reset và cảnh báo không nhập PII thật.
- Frontend nguồn còn hiển thị bốn mã Hôn nhân và gia đình ngoài data package hiện hành.

### 2026-07-17 — Core, rules và LiteLLM trên nhánh nguồn

- Thêm 27 deterministic rule handler, question selector, suggestion lifecycle và revision guard.
- Thêm LiteLLM provider, smoke command, giới hạn timeout/response và insecure-HTTP opt-in.
- LLM chỉ phân loại/trích xuất; required field, rule, phí, thời hạn và nguồn do code xác định xử lý.

### 2026-07-17 — Đồng bộ phạm vi Product & UX

- Cập nhật `doc/Product and UX.md` để chỉ hỗ trợ ba thủ tục trong data package v2: `2.000635`,
  `1.013314` và `1.004194`.
- Thay các persona, demo, field mẫu, chỉ số đánh giá và delivery output còn mô tả trích lục kết hôn/
  khai tử bằng nội dung tương ứng của xác nhận Mẫu số 02 và đăng ký tạm trú.
- Ghi rõ hệ thống không thay UBND cấp xã xác nhận tình trạng nhà/đất và không tự phê duyệt thủ tục cư trú.
