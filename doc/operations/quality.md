# Snapshot chất lượng VNeGuide

Thang điểm:

- **A:** đầy đủ, kiểm tra ổn định và có bằng chứng.
- **B:** hoạt động, còn thiếu nhỏ không ảnh hưởng luồng chính.
- **C:** mới hoạt động một phần hoặc chưa đủ test.
- **D:** chưa triển khai hoặc baseline đang hỏng.

## Domain sản phẩm

| Domain | Điểm hiện tại | Bằng chứng | Khoảng trống chính |
| --- | --- | --- | --- |
| Procedure catalog | A | Repository audit, schema và 12 checksum pass | Chưa kiểm tra freshness tự động |
| Source grounding | A | Source/status/procedure/local-path gate có unit test | Chưa tự refresh nguồn online |
| Structured extraction | D | Chưa có implementation | Thiếu provider adapter và contract test |
| Conversation flow | D | Chưa có implementation | Thiếu state machine nhiều lượt |
| Rule validation | C | Rule và 10 context input có contract/audit | Chưa có Python rule handlers; thiếu 17 positive cases |
| Terminal chatbot | D | Chưa có entrypoint | Chưa chạy được hội thoại end-to-end |

## Module kiến trúc

| Module | Điểm hiện tại | Trạng thái |
| --- | --- | --- |
| `domain` | B | Contract bất biến và unit test pass |
| `data` | B | Loader/repository/audit và unit test pass |
| `ai` | D | Mới có package skeleton |
| `core` | D | Mới có package skeleton |
| `rules` | D | Mới có package skeleton |
| `cli` | D | Mới có package skeleton |
| `tests` | C | 25 unit test pass; chưa có integration/E2E |

Chỉ nâng điểm khi có lệnh xác minh và artifact cụ thể; không nâng điểm dựa trên code chưa chạy.
