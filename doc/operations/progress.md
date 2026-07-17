# Nhật ký tiến độ VNeGuide

## Trạng thái đã xác minh hiện tại

- Repository: `D:\VAIC_UET`.
- Giai đoạn: domain/data foundation hoàn thành; chuẩn bị AI extraction cho Terminal MVP.
- Phạm vi nghiệp vụ: ba procedure pack trong `data/README.md`.
- Bootstrap chuẩn: chưa được triển khai.
- Lệnh chạy chatbot: chưa được triển khai.
- Runtime Python cài trên host: chưa có interpreter khả dụng.
- Xác minh gần nhất: compile 21 file Python và chạy 25 unit test bằng Python 3.11.9 embeddable; tất cả pass.
- Data check gần nhất: ba pack, 44 field, 10 rule-context input, 27 rule, 13 source và 12 checksum đều pass audit.
- Blocker chính: AI extraction, rule engine, conversation orchestrator và CLI chưa được triển khai.

## Ưu tiên tiếp theo

Triển khai `LLMProvider` và structured extraction trong `src/vneguide/ai/` dựa trên contract chung, bắt đầu bằng mock provider và không gọi model thật trong unit test.

## Nhật ký phiên

### 2026-07-17 — Chuẩn hóa repository

- Tạo cấu trúc `src/vneguide/` và `tests/` theo ranh giới bốn người.
- Chuyển dữ liệu runtime từ `data/data/` sang `data/catalog/`.
- Gom tài liệu nguồn vào `data/references/` và loại bỏ hai bản sao trùng byte-for-byte.
- Thêm registry cho nguồn context `1.004222` và cập nhật checksum.
- Commit nền gần nhất: `013d2be chore: reorganize repository data layout`.
- Chưa xác minh Python package vì môi trường không có Python interpreter.

### 2026-07-17 — Domain và data foundation (Người 1)

- Nhánh: `hautt`.
- Thêm enum/model/contract dùng chung cho đúng ba mã thủ tục data package v2.
- Thêm loader, dependency-free JSON Schema validator và `ProcedureRepository`.
- Repository audit deep-compare catalog, kiểm nguồn approved, chống path traversal, kiểm guidance step, rule input và checksum chuẩn LF.
- Thêm `rule_context_catalog.json` để khai báo 10 tín hiệu rule không phải field biểu mẫu.
- Siết validation-result schema và semantic validation cho procedure/rule/field/source.
- Ghi quyết định OD-004: MVP dùng handler xác định theo `rule_id`, không `eval/exec` chuỗi condition.
- Bằng chứng: compile 21 file và chạy 25 unit test bằng Python 3.11.9; kết quả `OK` trong 0,032 giây.
- Python embeddable và ZIP tạm đã được xóa sau kiểm thử.
