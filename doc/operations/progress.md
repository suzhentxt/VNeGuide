# Nhật ký tiến độ VNeGuide

## Trạng thái đã xác minh hiện tại

- Repository: `/Users/totrinh/Dev/VAIC_UET`.
- Giai đoạn: đã triển khai CLI/integration harness và phần Người 2 — LLM/structured extraction.
- Phạm vi nghiệp vụ: ba procedure pack trong `data/README.md`.
- Bootstrap chuẩn: đã có `pyproject.toml`, dev dependencies và quality gate.
- Lệnh CLI: `python -m vneguide.cli` đã có; còn chờ `vneguide.core:create_session` để chạy hội thoại end-to-end.
- Runtime test hiện tại: Python 3.11.14 tại `.venv/bin/python`; CLI trước đó cũng đã được xác minh trên Python 3.12.7.
- Data check gần nhất: 10 JSON và 2 JSONL parse thành công; năm `local_file` trong source register đều tồn tại.
- Structured extraction: provider-neutral interface, scripted mock, OpenAI Responses adapter,
  strict catalog-derived schema, bounded retry và fallback kỹ thuật đã triển khai.
- Check tích hợp sau rebase: Ruff lint/format đúng scope và Mypy strict đạt; Pytest
  `37 passed, 1 skipped`; `compileall` đạt.
- Blocker chính: domain contract, data loader và conversation core chưa được triển khai.

## Ưu tiên tiếp theo

Người 1 định nghĩa domain contract và data loader chính thức; sau đó map output AI-local sang
domain model trước khi Người 3 nối conversation orchestrator. Chạy live intent/slot eval riêng khi
có model và API key an toàn.

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
- Xác minh: Ruff, formatter và Mypy đạt; Pytest `9 passed, 1 skipped`, coverage `80.00%`.
- Giới hạn: live provider smoke test chưa chạy; core chưa cung cấp `vneguide.core:create_session`.

### 2026-07-17 — LLM và structured extraction

- Thêm `LLMProvider`, typed provider errors, `MockLLMProvider` và OpenAI Responses adapter dùng
  strict JSON Schema; cấu hình provider/model/key được đọc lazy từ biến môi trường và key không vào repr.
- Prompt và schema lấy procedure code/field/type/enum từ data package v2 đã review (`2.000635`,
  `1.013314`, `1.004194`), không dùng intent enum cũ trong tài liệu Terminal và không giao business
  validation/checklist/required field/source cho LLM.
- Validator kiểm exact output keys, procedure/field ownership, type, enum, pattern, bounds, ngày,
  evidence trong message, duplicate field; malformed output/timeout chỉ retry tối đa một lần rồi
  trả fallback tách biệt với `unsupported`.
- Adapter chỉ gửi bearer token tới đúng endpoint HTTPS OpenAI, không follow redirect, giới hạn
  response 2 MB; extractor giới hạn input 8.000 ký tự và copy schema giữa các call.
- Thêm `tests/evals/intent_cases.jsonl` gồm 16 case cho ba procedure, unsupported và ambiguous.
  Đây là contract fixture chạy qua scripted mock, chưa phải số đo accuracy của model thật.
- Lệnh đã chạy:
  - `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` — 28 test pass.
  - `pytest -q` bằng executable pytest trong uv cache — 28 pass, 41 subtest pass.
  - `ruff check` và `ruff format --check` cho `src/vneguide/ai` + test extractor — pass.
  - `PYTHONPATH=src .venv/bin/python -m compileall -q src/vneguide/ai tests/unit/test_extractor.py` — pass.
- Chưa gọi OpenAI thật và chưa đo NLU/slot accuracy vì phiên này không sử dụng API key; HTTP adapter
  được kiểm bằng fake transport.
- Sau khi rebase lên `origin/main`, full suite đạt: Ruff lint/format đúng scope, Mypy strict không lỗi,
  Pytest `37 passed, 1 skipped` và `compileall` pass.
