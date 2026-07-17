# Bàn giao phiên

## Trạng thái hiện tại

- Repo đã có cấu trúc module và data package v2.
- Scope runtime nằm trong `data/README.md`.
- Chưa có domain model, loader, orchestrator hoặc CLI chạy được.
- Sandbox gần nhất không có Python interpreter để chạy package/test.

## Việc đã xác minh

- JSON và JSONL trong data package parse được.
- Các nguồn local được đăng ký đều tồn tại.
- Repo không còn conflict marker sau lần kiểm tra gần nhất.

## Rủi ro

- Tài liệu Product/Architecture/Terminal cũ vẫn mô tả bộ thủ tục khác data package v2.
- Không được triển khai enum theo tài liệu cũ trước khi chốt domain contract.
- Git LFS có thể cần quyền ghi `.git/lfs/tmp` trong môi trường sandbox.

## Bước tốt nhất tiếp theo

Tạo domain contract tối thiểu từ JSON Schema và procedure pack hiện hành, sau đó thêm unit test bằng fixture/mocks trước khi tích hợp LLM.

## Lệnh dự kiến

- Cài đặt sau khi có Python 3.11+: `py -m pip install -e .`
- Test sau khi được cấu hình: `py -m pytest`
- CLI mục tiêu: `py -m vneguide.cli`

Các lệnh trên là mục tiêu chưa được xác minh trong môi trường hiện tại.
