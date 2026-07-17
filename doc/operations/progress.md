# Nhật ký tiến độ VNeGuide

## Trạng thái hiện tại

- Repository: `D:\VAIC_UET`, nhánh `dev`.
- Phạm vi nghiệp vụ là ba procedure pack trong `data/README.md`.
- Domain/data foundation, structured extraction, LiteLLM provider, deterministic rule engine,
  suggestion-aware conversation core và CLI harness đều đã có source.
- `python -m vneguide.cli` đã nạp được composition root `vneguide.core:create_session`.
- Provider trực tiếp hỗ trợ `mock`, OpenAI Responses và LiteLLM Chat Completions.
- Merge hiện tại kết hợp core/rules từ `origin/dev` với LiteLLM support cục bộ; quality gate của
  trạng thái hợp nhất được ghi ở phần xác minh bên dưới.

## Ưu tiên tiếp theo

Trước khi nối web, bổ sung interaction Accept/Reject/Edit cho terminal hoặc adapter dùng chung và
đưa các rule-context signal đã review vào luồng extraction/core. Sau đó chạy demo end-to-end bằng
dữ liệu tổng hợp. Không gửi dữ liệu hành chính thật qua gateway HTTP; cần HTTPS trước khi dùng
transcript thật.

## Xác minh trạng thái hợp nhất

- Compileall, Ruff, formatter và Mypy đều pass trên working tree kết hợp.
- Pytest: `87 passed, 1 skipped`; coverage `80.82%`, vượt gate `80%`.
- Terminal mock smoke khởi tạo `vneguide.core:create_session` và `/quit` an toàn.
- Provider-only smoke trước merge đã gọi thật `Qwen/Qwen3.5-9B` và trả
  `MODEL_SMOKE_OK ... structured_output=true` với schema tổng hợp `{ok: boolean}`.

## Nhật ký phiên

### 2026-07-17 — Hợp nhất core/rules và LiteLLM

- Nhập conversation core, 27 deterministic rule handler, question selector và
  `vneguide.core:create_session` từ `origin/dev`.
- Giữ provider LiteLLM, loader `.env` có chỉ định, Qwen `enable_thinking=false` và smoke command.
- Source/tests được Git hợp nhất tự động; conflict chỉ nằm trong ba tài liệu vận hành.
- Gate kết hợp: Ruff/format/Mypy pass; Pytest `87 passed, 1 skipped`; coverage `80.82%`.

### 2026-07-17 — LiteLLM self-hosted provider

- Thêm `LiteLLMChatCompletionsProvider` với strict JSON Schema, response-size/timeout gate, typed
  error và chặn redirect.
- Tách provider selector `litellm`, base URL và key riêng; HTTP yêu cầu insecure opt-in rõ ràng.
- Thêm `python -m vneguide.ai.smoke --env-file .env --confirm-live`; request chỉ dùng dữ liệu tổng
  hợp và không in prompt, raw response hoặc key.
- Pytest tại thời điểm triển khai: `74 passed, 1 skipped`; Ruff/format/Mypy pass cho AI và test
  liên quan.
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
- Khóa OD-004: rule engine dùng handler theo `rule_id`, không `eval/exec` condition.
- Bằng chứng trên nhánh nguồn: 25 unit test pass.

### 2026-07-17 — CLI và LLM structured extraction

- Thêm terminal loop, `/status`, `/reset`, `/quit`, renderer và integration port cho core.
- Thêm provider-neutral interface, mock/OpenAI adapter, strict schema, bounded retry và fallback.
- LLM chỉ phân loại/trích xuất; required field, rule, phí, thời hạn và nguồn do code xác định xử lý.
- Bằng chứng trước khi tích hợp domain/data: Pytest `37 passed, 1 skipped`.
