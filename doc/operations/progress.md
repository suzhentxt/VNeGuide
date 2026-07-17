# Nhật ký tiến độ VNeGuide

## Trạng thái đã xác minh hiện tại

- Repository: `D:\Workspace\VAIC_UET`.
- Giai đoạn: chuẩn bị nền cho Terminal MVP.
- Phạm vi nghiệp vụ: ba procedure pack trong `data/README.md`.
- Bootstrap chuẩn: đã có `pyproject.toml`, dev dependencies và quality gate.
- Lệnh CLI: `python -m vneguide.cli` đã có; còn chờ `vneguide.core:create_session` để chạy hội thoại end-to-end.
- Runtime đã xác minh: Python 3.12.7 trong `.venv` cục bộ.
- Data check gần nhất: 10 JSON và 2 JSONL parse thành công; năm `local_file` trong source register đều tồn tại.
- CLI check gần nhất: Ruff, formatter và Mypy đạt; Pytest `9 passed, 1 skipped`, coverage `80.00%`.
- Blocker chính: domain contract, loader và conversation core chưa được triển khai.

## Ưu tiên tiếp theo

Định nghĩa contract Python trong `src/vneguide/domain/` bám theo `data/contracts/` và `data/catalog/`, kèm unit test không gọi model thật.

## Nhật ký phiên

### 2026-07-17 — Chuẩn hóa repository

- Tạo cấu trúc `src/vneguide/` và `tests/` theo ranh giới bốn người.
- Chuyển dữ liệu runtime từ `data/data/` sang `data/catalog/`.
- Gom tài liệu nguồn vào `data/references/` và loại bỏ hai bản sao trùng byte-for-byte.
- Thêm registry cho nguồn context `1.004222` và cập nhật checksum.
- Commit nền gần nhất: `013d2be chore: reorganize repository data layout`.
- Chưa xác minh Python package vì môi trường không có Python interpreter.

### 2026-07-17 — CLI, integration harness và quality gate

- Thêm entry point `python -m vneguide.cli`, vòng lặp terminal và các lệnh `/status`, `/reset`, `/quit`.
- Tách CLI khỏi core qua `ConversationSession`/session factory; không định nghĩa lại domain model hoặc business rule.
- Renderer hiển thị các trường `TurnResult`, validation/source và che field định danh nhạy cảm.
- Thêm integration tests, fixture nghiệm thu bám ba procedure code trong `data/README.md`, secret scan và live smoke test opt-in.
- Hợp nhất hướng dẫn CLI với cấu trúc data package v2 trên `origin/main`.
- Xác minh: Ruff, formatter, Mypy đạt; Pytest `9 passed, 1 skipped`, coverage `80.00%`.
- Giới hạn: live provider smoke test chưa chạy; core chưa cung cấp `vneguide.core:create_session`.
