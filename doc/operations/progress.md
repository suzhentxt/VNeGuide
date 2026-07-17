# Nhật ký tiến độ VNeGuide

## Trạng thái đã xác minh hiện tại

- Repository hiện tại: `D:\VAIC_UET`.
- Nhánh: `dev`.
- Phạm vi nghiệp vụ: ba procedure pack trong `data/README.md`.
- Domain/data foundation, structured extraction, LiteLLM provider và CLI/integration harness đã có
  source.
- Bootstrap: `pyproject.toml` đã khai báo dev dependencies và quality tools.
- CLI: `python -m vneguide.cli` đã có entry point nhưng còn chờ `vneguide.core:create_session`.
- Rule engine và conversation orchestrator chưa được triển khai.
- Xác minh lịch sử gần nhất:
  - Domain/data: compile 21 file và 25 unit test pass trên Python 3.11.9.
  - AI + CLI trên `main`: Ruff/Mypy/compileall pass; Pytest `37 passed, 1 skipped`.
- Xác minh trạng thái hợp nhất ngày 2026-07-17 bằng Python 3.11.9 embeddable:
  - Compile toàn bộ 42 file Python thành công.
  - Unittest discovery chạy 63 test: `62 passed, 1 skipped` (live provider smoke test là opt-in).
  - Ruff, formatter, Mypy và Pytest chưa chạy lại vì runtime tạm không cài dev dependencies.
- Xác minh LiteLLM ngày 2026-07-17 bằng Python 3.11.9:
  - Pytest: `74 passed, 1 skipped`.
  - Ruff, formatter và Mypy đều pass trên `src/vneguide/ai/` cùng test LiteLLM liên quan.
  - Provider smoke gọi thật `Qwen/Qwen3.5-9B` và trả
    `MODEL_SMOKE_OK ... structured_output=true`; request chỉ dùng schema tổng hợp `{ok: boolean}`.
  - Full-repo Ruff còn một import-order lỗi và 10 file format cũ; full-repo Mypy còn 27 lỗi trong
    `data/repository.py`, `test_domain_contracts.py` và `test_data_repository.py`.

## Ưu tiên tiếp theo

Người 3 triển khai deterministic rule handlers và conversation orchestrator dựa trên
`vneguide.domain`, `ProcedureRepository` và `ExtractionResult`. Đồng thời thay AI-local wire model
bằng adapter rõ ràng sang shared domain contract; không định nghĩa lại procedure code hoặc field.

## Nhật ký phiên

### 2026-07-17 — LiteLLM self-hosted provider

- Thêm `LiteLLMChatCompletionsProvider` với strict JSON Schema, response-size/timeout gate, typed
  error, chặn redirect và Qwen `enable_thinking=false`.
- Tách provider selector `litellm` khỏi `VNEGUIDE_LITELLM_BASE_URL`; HTTP bị từ chối nếu chưa bật
  opt-in rõ ràng.
- Thêm loader `.env` có chỉ định, giới hạn kích thước/key và không thay đổi process environment.
- Thêm `python -m vneguide.ai.smoke --env-file .env --confirm-live`; lệnh không phụ thuộc core,
  không gửi catalog/PII và không in prompt, raw response hoặc key.
- Xác minh live với endpoint self-hosted: model `Qwen/Qwen3.5-9B` trả structured output hợp lệ.
- Giới hạn: endpoint hiện dùng HTTP public IP; chỉ dùng dữ liệu giả cho tới khi có HTTPS.

### 2026-07-17 — Chuẩn hóa repository

- Tạo cấu trúc `src/vneguide/` và `tests/` theo ranh giới bốn người.
- Chuyển dữ liệu runtime từ `data/data/` sang `data/catalog/`.
- Gom tài liệu nguồn vào `data/references/` và loại bỏ hai bản sao trùng byte-for-byte.
- Thêm registry cho nguồn context `1.004222` và cập nhật checksum.
- Commit: `013d2be chore: reorganize repository data layout`.

### 2026-07-17 — Domain và data foundation (Người 1)

- Nhánh nguồn: `hautt`.
- Thêm enum/model/contract dùng chung cho đúng ba mã thủ tục data package v2.
- Thêm loader, dependency-free JSON Schema validator và `ProcedureRepository`.
- Repository audit deep-compare catalog, kiểm nguồn approved, chống path traversal, kiểm guidance
  step, rule input và checksum chuẩn LF.
- Thêm `rule_context_catalog.json` để khai báo 10 tín hiệu rule không phải field biểu mẫu.
- Siết validation-result schema và semantic validation cho procedure/rule/field/source.
- Ghi OD-004: MVP dùng handler xác định theo `rule_id`, không `eval/exec` chuỗi condition.
- Bằng chứng: compile 21 file và chạy 25 unit test bằng Python 3.11.9, tất cả pass.
- Commit: `a8a21e4 feat: add domain and data foundation`.

### 2026-07-17 — CLI, integration harness và quality gate

- Thêm entry point `python -m vneguide.cli`, vòng lặp terminal và `/status`, `/reset`, `/quit`.
- Tách CLI khỏi core qua `ConversationSession`/session factory.
- Renderer hiển thị `TurnResult`, validation/source và che field định danh nhạy cảm.
- Thêm integration tests, acceptance fixture, secret scan và live smoke test opt-in.
- Xác minh tại thời điểm triển khai: Ruff, formatter và Mypy pass; Pytest `9 passed, 1 skipped`,
  coverage `80.00%`.
- Giới hạn: core chưa cung cấp `vneguide.core:create_session`.

### 2026-07-17 — LLM và structured extraction

- Thêm `LLMProvider`, typed provider errors, scripted mock và OpenAI Responses adapter.
- Prompt/schema được tạo từ data package đã review; LLM không quyết định checklist, required field,
  source hoặc business validation.
- Validator kiểm strict keys, procedure/field ownership, type, enum, pattern, bounds, date, evidence
  và duplicate field; retry có giới hạn và safe fallback.
- Thêm 16 intent fixtures cho ba procedure, unsupported và ambiguous.
- Không gọi OpenAI thật; HTTP adapter được kiểm bằng fake transport.
- Sau rebase trên CLI/main tại thời điểm đó: Ruff/Mypy/compileall pass; Pytest
  `37 passed, 1 skipped`.
