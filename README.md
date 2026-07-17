# VNeGuide

VNeGuide là chatbot hỗ trợ người dân chuẩn bị hồ sơ cấp bản sao trích lục hộ tịch.

Giai đoạn hiện tại chỉ tập trung vào chatbot chạy trong terminal. Chi tiết phân công xem tại [kế hoạch chia task](doc/Terminal%20MVP%20-%20Chia%20task%204%20nguoi.md).

## Cấu trúc source

```text
src/vneguide/
├── domain/     # Contract, enum và model dùng chung
├── data/       # Dữ liệu thủ tục và nguồn tham khảo
├── ai/         # LLM provider, prompt và extraction
├── core/       # Điều phối hội thoại và state
├── rules/      # Rule engine và validation
└── cli/        # Giao diện terminal

tests/
├── unit/
├── integration/
└── evals/
```

Không đặt business logic trong `cli/` và không định nghĩa lại model dùng chung ngoài `domain/`.
