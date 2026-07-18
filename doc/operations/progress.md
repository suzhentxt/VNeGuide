# Nhật ký tiến độ VNeGuide

## Trạng thái hiện tại

- Repository: `D:\VAIC_UET`, nhánh `dev`; source hiện kết hợp LiteLLM/core/rules với HTTP API và
  demoweb từ `main`.
- Phạm vi nghiệp vụ đã review vẫn là ba procedure pack trong `data/README.md`.
- Domain/data foundation, structured extraction, LiteLLM provider, deterministic rule engine,
  suggestion-aware conversation core và CLI harness đều đã có source.
- `python -m vneguide.cli` nạp composition root `vneguide.core:create_session`.
- Provider trực tiếp hỗ trợ `mock`, OpenAI Responses và LiteLLM Chat Completions.
- FastAPI Chat API, Next.js BFF và chatbox route-scoped cho mục Hôn nhân và gia đình đã được
  triển khai; API hỗ trợ send/Accept/Reject/Edit/reset.
- Bốn procedure code đang có luồng giao diện trên web chưa thuộc data package backend hiện hành;
  API/UI phải tiếp tục cảnh báo ngoài phạm vi và không tự suy đoán rule hoặc checklist.

## Ưu tiên tiếp theo

Trước khi deploy hoặc mở demoweb ra Internet, xử lý các advisory production bằng một lượt nâng
dependency có review và chạy lại web gate. Với luồng nghiệp vụ, review/bổ sung data package đã dẫn
nguồn cho bốn mã thủ tục Hôn nhân và gia đình đang hiển thị trên web, đồng thời đưa các rule-context
signal đã review vào extraction/core. Sau đó chạy demo end-to-end bằng dữ liệu tổng hợp. Không gửi dữ
liệu hành chính thật qua gateway HTTP; cần HTTPS trước khi dùng transcript thật.

## Bằng chứng xác minh sau merge

- Python 3.11.9 trên working tree hợp nhất: Compileall, Ruff lint/format và Mypy strict đều pass.
- Pytest `91 passed, 1 skipped`; coverage `80.64%`, vượt gate `80%`.
- Terminal mock smoke khởi tạo `vneguide.core:create_session` và `/quit` an toàn, không gọi provider
  ngoài.
- `demoweb`: `npm run check` pass; ESLint, TypeScript và Next.js production build đủ 29 route.
- `npm audit --omit=dev` báo `12 vulnerabilities` (`1 low`, `7 moderate`, `4 high`). Chưa tự chạy
  `npm audit fix` vì cần review thay đổi dependency/lockfile và regression test riêng.
- Provider-only smoke trước merge đã gọi thật `Qwen/Qwen3.5-9B` và trả
  `MODEL_SMOKE_OK ... structured_output=true` với schema tổng hợp `{ok: boolean}`.

## Nhật ký phiên

### 2026-07-18 — Kết nối lại model thật với chatbot web

- Xác định lỗi trực tiếp là FastAPI cổng `8000` đã dừng; web cổng `3000` vẫn chạy nhưng BFF trả
  `503 chat_api_unavailable`, nên tin nhắn chưa tới model.
- Thêm tùy chọn khởi động `python -m vneguide.api --env-file .env`; composition root chỉ đọc file
  LLM khi người chạy opt-in tường minh, không tự nạp secret lúc import.
- Nâng timeout BFF từ 25 lên 60 giây để bao phủ tối đa hai lượt provider, mỗi lượt 20 giây; widget tự
  tạo lại session và gửi lại một lần khi cookie trỏ tới session backend đã mất/hết hạn.
- Live BFF smoke bằng dữ liệu giả: API health `ok`, tạo session `201`, message `200` trong 1,34 giây;
  model nhận diện `1.004194`, trả `ask_clarification`, 11 field thiếu, 5 nguồn và 1 assistant message.
- Gate sau sửa: Ruff/format pass, Mypy pass, Pytest `94 passed, 1 skipped`, coverage `80.97%`;
  `npm run check` pass với ESLint, TypeScript và Next.js production build đủ 29 route.
- Giới hạn xác minh: không có tab in-app browser được gắn vào phiên, nên thao tác click trực quan chưa
  được tự động hóa; live smoke đã đi qua cùng `/api/chat/session` và `/api/chat/message` mà browser dùng.

### 2026-07-18 — Giảm nhiễu hydration do extension trình duyệt

- Xác nhận HTML gốc của demoweb không chứa `mdl-js`, `data-qb-installed` hoặc script sửa
  `document.documentElement`; các thuộc tính này được extension trình duyệt chèn trước khi React hydrate.
- Thêm `suppressHydrationWarning` trực tiếp trên thẻ `<html>` của root layout để extension sửa thuộc tính
  root không làm Next.js hiện development error overlay; các mismatch bên trong cây ứng dụng vẫn được báo.
- Gate sau sửa: `npm run check` pass; ESLint, TypeScript và Next.js production build đủ 29 route.
- Giới hạn: thay đổi này không ngăn extension sửa DOM. Khi chẩn đoán hydration thật, tắt extension trên
  localhost hoặc dùng profile sạch/Incognito rồi hard reload.

### 2026-07-18 — Hợp nhất HTTP API/demoweb vào dev

- Merge source `main` tại `d5921ca` vào `dev`, giữ đồng thời LiteLLM/core/rules và FastAPI/BFF/web.
- Conflict chỉ nằm ở `.env.example`, `progress.md` và `session-handoff.md`; cấu hình LiteLLM và API
  local đều được giữ, không thêm secret thật.
- Format cơ học `src/vneguide/api/session_store.py` để working tree đạt formatter hiện hành.
- Gate hợp nhất: Compileall/Ruff/format/Mypy pass; Pytest `91 passed, 1 skipped`, coverage `80.64%`;
  `npm run check` pass với 29 route.
- Npm audit còn 12 advisory production, gồm 4 mức high; cần xử lý trước khi deploy Internet.

### 2026-07-18 — Nối HTTP API và chatbox demoweb

- Thêm FastAPI adapter với session ID ngẫu nhiên, TTL, capacity limit, per-session lock và endpoint
  send/Accept/Reject/Edit/reset.
- Thêm serializer HTTP tường minh cho `TurnResult`; trả field label/source từ data package và không
  trả raw prompt/model output.
- Thêm Next.js BFF `/api/chat/*`; session ID nằm trong cookie `HttpOnly`, URL backend và API key
  không lộ cho browser.
- Thêm chatbox responsive, accessible, dùng palette hiện hành và chỉ mount trong
  `/hon-nhan-va-gia-dinh/**`.
- Chatbox có card Accept/Sửa/Từ chối, field thiếu, validation, nguồn, cảnh báo PII, reset và xử lý
  chuyển route.
- Bốn procedure code trên web chưa thuộc data package backend hiện hành; API/UI hiển thị cảnh báo
  scope, không tự suy đoán rule/checklist.
- Bằng chứng trên nhánh nguồn: luồng local web `3001` → BFF → API `8001` tạo session `201`, message
  `200`; mock rỗng trả safe fallback `retry` đúng thiết kế. Route scope và các quality gate được ghi
  tại phần bằng chứng xác minh trước merge.

### 2026-07-18 — Bổ sung demoweb Next.js

- Thêm `demoweb/` làm ứng dụng giao diện chạy độc lập trong repository VNeGuide.
- Bundle chỉ gồm `src/`, `public/`, manifest/lockfile và cấu hình cần để chạy Next.js; không kèm tool
  clone, HTML/ảnh chụp nguồn, `_DataURI`, cache build hoặc `node_modules`.
- Chuẩn hóa package thành `demoweb@1.0.0` và loại metadata của template clone.
- Bằng chứng trước khi chuyển: ESLint pass, TypeScript pass và Next.js production build pass với 26
  route.

### 2026-07-18 — Sửa lỗi luồng demoweb sau tích hợp

- Danh mục Hôn nhân và gia đình liên kết đúng 4 thủ tục đã tích hợp ở frontend; 11 thủ tục còn lại
  hiển thị `Chưa tích hợp` và không còn route fallback sai.
- Trang xem tất cả tổng hợp đủ 7 dịch vụ, tìm kiếm không phân biệt dấu theo tên, mã thủ tục và cơ
  quan.
- Bắt buộc chọn rõ dịch vụ và đơn vị tiếp nhận; lựa chọn hợp lệ được giữ xuyên suốt danh sách,
  wizard, tờ khai và liên kết quay lại mà không đưa PII vào URL.
- Trạng thái lưu tờ khai dùng marker theo phiên không chứa PII; tham số `to-khai=da-luu` tùy ý không
  còn tạo trạng thái hoàn thành giả.
- Bỏ mặc định Hà Nội/Cầu Giấy và dữ liệu cá nhân mẫu khỏi form; sidebar dùng 34 tỉnh/thành, 24
  bộ/ngành và trạng thái tải/thử lại rõ ràng.
- Proxy cơ quan có timeout, kiểm tra/chuẩn hóa dữ liệu, loại trùng, giới hạn 500 bản ghi và phản hồi
  lỗi có kiểm soát.
- Bằng chứng trên nhánh nguồn: `npm run check` pass; 12 HTTP assertion production pass cho catalog,
  tìm kiếm, lựa chọn, redirect và API validation.

### 2026-07-18 — Cảnh báo minh bạch bản mô phỏng

- Thêm banner cảnh báo toàn cục trên mọi route: đây không phải website Chính phủ, chỉ là bản mô
  phỏng Hackathon và không tiếp nhận hồ sơ/dữ liệu cá nhân thật.
- Đổi application name, title, description và author sang ngữ cảnh Hackathon; cấu hình robots thành
  `noindex`, `nofollow`, `nocache` để tránh bị hiểu nhầm là dịch vụ chính thức.

### 2026-07-17 — Hợp nhất core/rules và LiteLLM

- Nhập conversation core, 27 deterministic rule handler, question selector và
  `vneguide.core:create_session` từ `origin/dev`.
- Giữ provider LiteLLM, loader `.env` có chỉ định, Qwen `enable_thinking=false` và smoke command.
- Source/tests được Git hợp nhất tự động; conflict chỉ nằm trong ba tài liệu vận hành.
- Gate kết hợp tại thời điểm đó: Ruff/format/Mypy pass; Pytest `87 passed, 1 skipped`; coverage
  `80.82%`.

### 2026-07-17 — LiteLLM self-hosted provider

- Thêm `LiteLLMChatCompletionsProvider` với strict JSON Schema, response-size/timeout gate, typed
  error và chặn redirect.
- Tách provider selector `litellm`, base URL và key riêng; HTTP yêu cầu insecure opt-in rõ ràng.
- Thêm `python -m vneguide.ai.smoke --env-file .env --confirm-live`; request chỉ dùng dữ liệu tổng
  hợp và không in prompt, raw response hoặc key.
- Pytest tại thời điểm triển khai: `74 passed, 1 skipped`; Ruff/format/Mypy pass cho AI và test liên
  quan.
- Live provider smoke với `Qwen/Qwen3.5-9B` đã pass structured output tối thiểu.

### 2026-07-17 — Conversation engine, rules và validation (Người 3)

- Thêm handler xác định cho 27 rule, field validation, missing-field resolver và question selector.
- Thêm state machine suggestion `pending/accepted/rejected/edited`, revision guard và retry cap.
- Cung cấp `vneguide.core:create_session`; CLI với mock rỗng trả fallback an toàn.
- Bằng chứng trên nhánh nguồn: Ruff/Mypy pass; Pytest `75 passed, 1 skipped`; coverage `82.64%`.

### 2026-07-17 — Domain và data foundation (Người 1)

- Thêm enum/model/contract dùng chung cho ba mã thủ tục data package v2.
- Thêm loader, dependency-free JSON Schema validator và `ProcedureRepository`.
- Audit catalog, nguồn approved, local path, rule input, guidance step và checksum chuẩn LF.
- Thêm `rule_context_catalog.json` cho 10 tín hiệu rule không phải field biểu mẫu.
- Khóa OD-004: rule engine dùng handler theo `rule_id`, không `eval/exec` condition.
- Bằng chứng trên nhánh nguồn: 25 unit test pass.

### 2026-07-17 — CLI và LLM structured extraction

- Thêm terminal loop, `/status`, `/reset`, `/quit`, renderer và integration port cho core.
- Thêm provider-neutral interface, mock/OpenAI adapter, strict schema, bounded retry và fallback.
- LLM chỉ phân loại/trích xuất; required field, rule, phí, thời hạn và nguồn do code xác định xử lý.
- Bằng chứng trước khi tích hợp domain/data: Pytest `37 passed, 1 skipped`.

### 2026-07-17 — Chuẩn hóa repository

- Tạo cấu trúc `src/vneguide/` và `tests/` theo ranh giới bốn người.
- Chuyển dữ liệu runtime sang `data/catalog/` và gom tài liệu nguồn vào `data/references/`.
- Thêm registry nguồn và checksum cho data package.
