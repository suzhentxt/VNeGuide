# Nhật ký tiến độ VNeGuide

## Trạng thái đã xác minh hiện tại

- Repository: `D:\VAIC_UET`.
- Giai đoạn: chuẩn bị nền cho Terminal MVP.
- Phạm vi nghiệp vụ: ba procedure pack trong `data/README.md`.
- Bootstrap chuẩn: chưa được triển khai.
- Lệnh chạy chatbot: chưa được triển khai.
- Runtime Python trong sandbox gần nhất: chưa có interpreter khả dụng.
- Data check gần nhất: 10 JSON và 2 JSONL parse thành công; năm `local_file` trong source register đều tồn tại.
- Blocker chính: domain contract và runtime chatbot chưa được triển khai.

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
