# VNeGuide – Domain & Data Package v2

## Phạm vi duy nhất
VNeGuide chỉ hỗ trợ ba thủ tục:
1. **2.000635** – Cấp bản sao Trích lục hộ tịch (**bản sao Giấy khai sinh**).
2. **1.013314** – Xác nhận điều kiện diện tích bình quân nhà ở và tình trạng chỗ ở để đăng ký thường trú tại chỗ thuê, mượn, ở nhờ.
3. **1.004194** – Đăng ký tạm trú.

Không còn procedure pack cho trích lục kết hôn, trích lục khai tử hoặc các thủ tục trước đây.

## Quyết định nghiệp vụ chính
- Mọi checklist/rule phải truy ngược tới `source_id`.
- Dataset Hugging Face chỉ dùng discovery và RAG seed.
- LLM không được tự thêm/bỏ giấy tờ, phí, thời hạn hoặc điều kiện.
- Thủ tục 1.013314: VNeGuide kiểm tra biểu mẫu và tính diện tích; UBND cấp xã mới có quyền xác nhận không tranh chấp, quyền sở hữu/sử dụng và địa điểm cấm.
- Thủ tục 1.004194: tự động kiểm tra cá nhân/hộ gia đình; trường hợp theo danh sách, lực lượng vũ trang và quốc tịch đặc biệt chuyển `needs_official_review`.
- Trạng thái cuối: `ready_to_submit`, `needs_correction`, `needs_official_review`, `out_of_scope`.

## Tệp chính
- `catalog/source_register.json`
- `catalog/procedure_packs/*.json`
- `catalog/field_catalog.json`
- `catalog/validation_rules.json`
- `catalog/rule_context_catalog.json`
- `contracts/*.schema.json`
- `evaluation/gold_guidance.jsonl`
- `evaluation/gold_validation.jsonl`
- `docs/review_workflow.md`
- `docs/open_decisions.json`

## Cấu trúc

```text
data/
├── catalog/          # Dữ liệu runtime đã chuẩn hóa
├── contracts/        # JSON Schema
├── evaluation/       # Ground-truth cases
├── qa/               # SHA-256 checksums
├── references/       # Bản lưu tài liệu nguồn
├── docs/             # Review workflow và quyết định
├── dichvucong/       # Dataset discovery/RAG seed
└── thutuchanhchinh/  # Dataset discovery/RAG seed
```

Không đặt tài liệu nguồn trực tiếp tại root `data/`. Không sao chép `catalog/` vào `src/`; application phải đọc package này qua loader.

Checksum trong `qa/` được tính trên nội dung UTF-8 với newline chuẩn hóa về LF. Quy ước này giúp cùng một artifact có hash ổn định trên Windows, Linux và macOS.

`field_catalog.json` chỉ chứa trường hồ sơ/người dùng. Những tín hiệu phục vụ rule nhưng không phải field biểu mẫu (ví dụ `ct01_missing`) phải được khai báo trong `rule_context_catalog.json`; không được tạo ngầm trong rule engine.

Ngày kiểm chứng: 2026-07-17.
