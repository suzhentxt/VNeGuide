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

## Ưu tiên tiếp theo

Người 4 nối hành động Accept/Reject/Edit vào UI/web adapter và cấu hình provider cho demo thật.

### 2026-07-17 — Conversation engine, rules và validation (Người 3)

- Tích hợp domain/data foundation từ commit Người 1 trước khi triển khai core.
- Thêm handler xác định cho toàn bộ 27 rule, field validation, missing-field resolver và question selector.
- Thêm state machine suggestion `pending/accepted/rejected/edited`, revision guard và retry cap.
- Cung cấp `vneguide.core:create_session`; CLI smoke chạy và trả fallback an toàn với mock rỗng.
- Xác minh Python 3.11.9: Ruff pass, Mypy strict pass, Pytest `75 passed, 1 skipped`, coverage `82.64%`.

## Nhật ký phiên

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
