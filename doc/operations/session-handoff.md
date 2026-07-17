# Bàn giao phiên

## Trạng thái hiện tại

- Repo có data package v2, domain/data runtime foundation, AI extraction và CLI shell.
- Scope runtime nằm trong `data/README.md`.
- `vneguide.domain` cung cấp contract dùng chung; `ProcedureRepository` cung cấp dữ liệu đã audit.
- `python -m vneguide.cli` nạp được `vneguide.core:create_session`.
- Core và rules đã hỗ trợ suggestion, Accept/Reject/Edit, validation và question selection.

## Việc đã xác minh

- Nhánh Người 1 có 25 unit test pass cho domain/data foundation.
- Baseline main trước tích hợp đạt `37 passed, 1 skipped`.
- AI tests không cần API key; live provider smoke mặc định skip.
- Data repository kiểm nguồn approved, local path, rule context và checksum.
- Python 3.11.9: Ruff và Mypy pass; Pytest `75 passed, 1 skipped`; coverage `82.64%`.

## Rủi ro

- Tài liệu Product/Architecture/Terminal cũ vẫn mô tả bộ thủ tục khác data package v2.
- Fixture intent scripted mock không chứng minh accuracy model thật.
- Rule condition không phải DSL thực thi; phải dùng handler xác định theo `rule_id`.
- Một số rule dùng context/document signal, không được suy đoán từ field biểu mẫu.
- Git LFS có thể cần quyền ghi `.git/lfs/tmp` trong môi trường sandbox.

## Bước tốt nhất tiếp theo

Người 4 nối session API vào web/widget, hiển thị suggestion card và cấu hình provider/model cho demo.

## Lệnh dự kiến

- Cài dev dependencies: `python -m pip install -e ".[dev]"`
- Quality gate: `python -m ruff check .`, `python -m mypy`, `python -m pytest`
- CLI: `python -m vneguide.cli`
