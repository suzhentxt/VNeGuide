# Nhật ký tiến độ VNeGuide

## Trạng thái đã xác minh hiện tại

- Phạm vi nghiệp vụ: ba procedure pack trong `data/README.md`.
- Domain/data foundation, CLI/integration harness và LLM structured extraction đã được triển khai.
- `vneguide.domain` cung cấp enum, model và contract dùng chung.
- `ProcedureRepository` load/audit pack, catalog, source, rule context và checksum.
- CLI có entry point `python -m vneguide.cli` và đã nạp được `vneguide.core:create_session`.
- Structured extraction có mock/OpenAI adapter, strict schema, bounded retry và safe fallback.
- Baseline trước khi tích hợp domain/data: Pytest `37 passed, 1 skipped`.
- Rule engine và suggestion-aware conversation orchestrator đã được triển khai.
- HTTP Chat API, Next.js BFF và chatbox route-scoped cho mục Hôn nhân và gia đình đã được triển khai.

## Ưu tiên tiếp theo

Review/bổ sung data package cho bốn mã thủ tục Hôn nhân và gia đình đang hiển thị trên web, sau đó cấu hình provider/model cho demo thật.

### 2026-07-17 — Conversation engine, rules và validation (Người 3)

- Tích hợp domain/data foundation từ commit Người 1 trước khi triển khai core.
- Thêm handler xác định cho toàn bộ 27 rule, field validation, missing-field resolver và question selector.
- Thêm state machine suggestion `pending/accepted/rejected/edited`, revision guard và retry cap.
- Cung cấp `vneguide.core:create_session`; CLI smoke chạy và trả fallback an toàn với mock rỗng.
- Xác minh Python 3.11.9: Ruff pass, Mypy strict pass, Pytest `75 passed, 1 skipped`, coverage `82.64%`.

## Nhật ký phiên

### 2026-07-18 — Nối HTTP API và chatbox demoweb

- Thêm FastAPI adapter với session ID ngẫu nhiên, TTL, capacity limit, per-session lock và endpoint send/Accept/Reject/Edit/reset.
- Thêm serializer HTTP tường minh cho `TurnResult`; trả field label/source từ data package và không trả raw prompt/model output.
- Thêm Next.js BFF `/api/chat/*`; session ID nằm trong cookie `HttpOnly`, URL backend và API key không lộ cho browser.
- Thêm chatbox responsive, accessible, dùng palette hiện hành và chỉ mount trong `/hon-nhan-va-gia-dinh/**`.
- Chatbox có card Accept/Sửa/Từ chối, field thiếu, validation, nguồn, cảnh báo PII, reset và xử lý chuyển route.
- Bốn procedure code trên web chưa thuộc data package backend hiện hành; API/UI hiển thị cảnh báo scope, không tự suy đoán rule/checklist.
- Xác minh end-to-end local trên web `3001` → BFF → API `8001`: tạo session `201`, message `200`; mock rỗng trả safe fallback `retry` đúng thiết kế.
- Xác minh route scope: trang chủ không có chatbox, `/hon-nhan-va-gia-dinh` có chatbox.
- Quality gates: Ruff pass, Mypy strict pass, Pytest `79 passed, 1 skipped`, coverage `82.32%`; `npm run check` pass với 29 route build.

### 2026-07-18 — Bổ sung demoweb Next.js

- Thêm `demoweb/` làm ứng dụng giao diện chạy độc lập trong repository VNeGuide.
- Bundle chỉ gồm `src/`, `public/`, manifest/lockfile và cấu hình cần để chạy Next.js; không kèm tool clone, HTML/ảnh chụp nguồn, `_DataURI`, cache build hoặc `node_modules`.
- Chuẩn hóa package thành `demoweb@1.0.0` và loại metadata của template clone.
- Xác minh trước khi chuyển: ESLint pass, TypeScript pass và Next.js production build pass với 26 route.

### 2026-07-18 — Sửa lỗi luồng demoweb sau tích hợp

- Danh mục Hôn nhân và gia đình liên kết đúng 4 thủ tục đã tích hợp; 11 thủ tục còn lại hiển thị `Chưa tích hợp` và không còn route fallback sai.
- Trang xem tất cả tổng hợp đủ 7 dịch vụ, tìm kiếm không phân biệt dấu theo tên, mã thủ tục và cơ quan.
- Bắt buộc chọn rõ dịch vụ và đơn vị tiếp nhận; lựa chọn hợp lệ được giữ xuyên suốt danh sách, wizard, tờ khai và liên kết quay lại mà không đưa PII vào URL.
- Trạng thái lưu tờ khai dùng marker theo phiên không chứa PII; tham số `to-khai=da-luu` tùy ý không còn tạo trạng thái hoàn thành giả.
- Bỏ mặc định Hà Nội/Cầu Giấy và dữ liệu cá nhân mẫu khỏi form; sidebar dùng 34 tỉnh/thành, 24 bộ/ngành và trạng thái tải/thử lại rõ ràng.
- Proxy cơ quan có timeout, kiểm tra/chuẩn hóa dữ liệu, loại trùng, giới hạn 500 bản ghi và phản hồi lỗi có kiểm soát.
- Xác minh: `npm run check` pass; 12 HTTP assertion production pass cho catalog, tìm kiếm, lựa chọn, redirect và API validation.

### 2026-07-18 — Cảnh báo minh bạch bản mô phỏng

- Thêm banner cảnh báo toàn cục trên mọi route: đây không phải website Chính phủ, chỉ là bản mô phỏng Hackathon và không tiếp nhận hồ sơ/dữ liệu cá nhân thật.
- Đổi application name, title, description và author sang ngữ cảnh Hackathon; cấu hình robots thành `noindex`, `nofollow`, `nocache` để tránh bị hiểu nhầm là dịch vụ chính thức.

### 2026-07-17 — Chuẩn hóa repository

- Tạo cấu trúc `src/vneguide/` và `tests/` theo ranh giới bốn người.
- Chuyển dữ liệu runtime sang `data/catalog/` và gom tài liệu nguồn vào `data/references/`.
- Thêm registry nguồn và checksum cho data package.

### 2026-07-17 — CLI, integration harness và quality gate

- Thêm entry point, các lệnh `/status`, `/reset`, `/quit` và integration port cho core.
- Renderer che field định danh nhạy cảm và hiển thị trạng thái hồ sơ.
- Thêm integration/eval fixtures, secret scan và live smoke test opt-in.

### 2026-07-17 — LLM và structured extraction

- Thêm provider-neutral interface, scripted mock, OpenAI Responses adapter và strict structured output.
- Schema lấy procedure code và field constraint từ data package v2; LLM không quyết định business rule.
- Thêm bounded retry, safe fallback và 16 intent/slot contract cases.
- Chưa chạy live model eval vì không sử dụng API key.

### 2026-07-17 — Domain và data foundation (Người 1)

- Thêm enum/model/contract dùng chung cho ba mã thủ tục data package v2.
- Thêm loader, JSON Schema validator và `ProcedureRepository`.
- Repository audit catalog, nguồn approved, local path, rule input và checksum.
- Thêm `rule_context_catalog.json` cho 10 tín hiệu rule không phải field biểu mẫu.
- Khóa quyết định OD-004: rule engine dùng handler theo `rule_id`, không `eval/exec` condition.
- Bằng chứng trên nhánh Người 1: 25 unit test pass.
