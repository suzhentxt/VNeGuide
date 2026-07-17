# Bàn giao phiên

## Trạng thái hiện tại

- Repo đã có cấu trúc module và data package v2.
- Scope runtime nằm trong `data/README.md`.
- CLI shell, renderer, integration port và quality tooling đã được triển khai.
- `python -m vneguide.cli` đã là entry point hợp lệ nhưng chưa xử lý hội thoại vì core chưa cung cấp `vneguide.core:create_session`.
- Chưa có domain model, data loader hoặc conversation orchestrator.
- Python 3.12.7 và dev dependencies đã được xác minh trong `.venv` cục bộ.

## Việc đã xác minh

- JSON và JSONL trong data package parse được.
- Các nguồn local được đăng ký đều tồn tại.
- Ruff, formatter và Mypy đều đạt.
- Pytest đạt `9 passed, 1 skipped`; coverage `80.00%`.
- Repo không còn conflict marker sau merge gần nhất.

## Rủi ro

- Tài liệu Product/Architecture/Terminal cũ vẫn mô tả bộ thủ tục khác data package v2.
- Không được triển khai enum theo tài liệu cũ trước khi chốt domain contract.
- Git LFS có thể cần quyền ghi `.git/lfs/tmp` trong môi trường sandbox.
- Live provider smoke test đang skip và chưa có bằng chứng gọi model thật.

## Bước tốt nhất tiếp theo

Tạo domain contract tối thiểu từ JSON Schema và procedure pack hiện hành, sau đó thêm unit test bằng fixture/mocks trước khi tích hợp LLM.

## Lệnh dự kiến

- Cài dev dependencies: `python -m pip install -e ".[dev]"`
- Quality gate: `python -m ruff check .`, `python -m mypy`, `python -m pytest`
- CLI: `python -m vneguide.cli`

Các lệnh quality gate đã được xác minh. CLI hiện trả thông báo cấu hình an toàn cho đến khi `vneguide.core:create_session` được triển khai.
