# Bàn giao phiên

## Trạng thái hiện tại

- Repo có data package v2, domain/data runtime foundation, AI extraction và CLI shell.
- Scope runtime nằm trong `data/README.md`.
- `vneguide.domain` cung cấp contract dùng chung; `ProcedureRepository` cung cấp dữ liệu đã audit.
- `python -m vneguide.cli` còn chờ `vneguide.core:create_session` để chạy hội thoại end-to-end.
- Core và rules chưa được triển khai.

## Việc đã xác minh

- Nhánh Người 1 có 25 unit test pass cho domain/data foundation.
- Baseline main trước tích hợp đạt `37 passed, 1 skipped`.
- AI tests không cần API key; live provider smoke mặc định skip.
- Data repository kiểm nguồn approved, local path, rule context và checksum.

## Rủi ro

- Tài liệu Product/Architecture/Terminal cũ vẫn mô tả bộ thủ tục khác data package v2.
- Fixture intent scripted mock không chứng minh accuracy model thật.
- Rule condition không phải DSL thực thi; phải dùng handler xác định theo `rule_id`.
- Một số rule dùng context/document signal, không được suy đoán từ field biểu mẫu.
- Git LFS có thể cần quyền ghi `.git/lfs/tmp` trong môi trường sandbox.

## Bước tốt nhất tiếp theo

Triển khai rule engine và conversation orchestrator của Người 3 trên contract domain/data hiện có, sau đó cung cấp `vneguide.core:create_session` cho CLI.

## Lệnh dự kiến

- Cài dev dependencies: `python -m pip install -e "[dev]"`
- Quality gate: `python -m ruff check .`, `python -m mypy`, `python -m pytest`
- CLI: `python -m vneguide.cli`
