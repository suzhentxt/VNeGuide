# Snapshot chất lượng VNeGuide

Thang điểm:

- **A:** đầy đủ, kiểm tra ổn định và có bằng chứng.
- **B:** hoạt động, còn thiếu nhỏ không ảnh hưởng luồng chính.
- **C:** mới hoạt động một phần hoặc chưa đủ test.
- **D:** chưa triển khai hoặc baseline đang hỏng.

## Domain sản phẩm

| Domain | Điểm hiện tại | Bằng chứng | Khoảng trống chính |
| --- | --- | --- | --- |
| Procedure catalog | B | JSON parse được, có schema và checksum | Chưa có loader/runtime test |
| Source grounding | B | Source register và local references tồn tại | Chưa kiểm tra freshness tự động |
| Structured extraction | D | Chưa có implementation | Thiếu provider adapter và contract test |
| Conversation flow | D | Chưa có implementation | Thiếu state machine nhiều lượt |
| Rule validation | C | Có rule catalog và gold validation | Chưa có Python rule engine |
| Terminal chatbot | D | Chưa có entrypoint | Chưa chạy được hội thoại end-to-end |

## Module kiến trúc

| Module | Điểm hiện tại | Trạng thái |
| --- | --- | --- |
| `domain` | D | Mới có package skeleton |
| `data` | C | Data package có sẵn, loader chưa có |
| `ai` | D | Mới có package skeleton |
| `core` | D | Mới có package skeleton |
| `rules` | D | Mới có package skeleton |
| `cli` | D | Mới có package skeleton |
| `tests` | D | Mới có cấu trúc thư mục |

Chỉ nâng điểm khi có lệnh xác minh và artifact cụ thể; không nâng điểm dựa trên code chưa chạy.
