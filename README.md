# VNeGuide

VNeGuide là chatbot hỗ trợ người dân chuẩn bị và kiểm tra trước hồ sơ dịch vụ công.

Giai đoạn hiện tại tập trung vào chatbot chạy trong terminal. Phạm vi nghiệp vụ đang triển khai được khóa trong [`data/README.md`](data/README.md); các tài liệu sản phẩm cũ trong `doc/` cần được đối chiếu với data package trước khi dùng để code.

## Cấu trúc repository

```text
data/
├── catalog/       # Procedure packs, field catalog, rules và source register
├── contracts/     # JSON Schema dùng để validate data package
├── evaluation/    # Bộ dữ liệu đánh giá có ground truth
├── references/    # Tài liệu nguồn được lưu cục bộ
├── qa/            # Checksum kiểm tra tính toàn vẹn
├── docs/          # Quy trình review và quyết định của data package
└── */             # Dataset discovery/RAG seed

doc/               # Requirement, product, architecture và kế hoạch
src/vneguide/      # Source code ứng dụng
tests/             # Unit, integration và evaluation tests
```

## Cấu trúc source code

```text
src/vneguide/
├── domain/     # Contract, enum và model dùng chung
├── data/       # Loader/repository truy cập data package ở root
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

## Quy ước

- `data/catalog/` là nguồn dữ liệu runtime đã chuẩn hóa; không tạo thêm một bản sao trong `src/`.
- `src/vneguide/data/` chỉ chứa code đọc và kiểm tra data package.
- Tài liệu nguồn chỉ lưu tại `data/references/`.
- Dataset discovery không được dùng trực tiếp để kết luận nghiệp vụ.
- Không commit `.env`, API key, cache, log hoặc dữ liệu cá nhân thật.
