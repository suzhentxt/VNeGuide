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
| Structured extraction | B | Mock/OpenAI adapter, strict schema và 28 unit test pass | Chưa có domain adapter và live model accuracy |
| Conversation flow | D | Chưa có implementation | Thiếu state machine nhiều lượt |
| Rule validation | C | Có rule catalog và gold validation | Chưa có Python rule engine |
| Terminal chatbot | C | Có entrypoint, renderer và integration test | Chưa chạy được hội thoại end-to-end vì thiếu core |

## Module kiến trúc

| Module | Điểm hiện tại | Trạng thái |
| --- | --- | --- |
| `domain` | D | Mới có package skeleton |
| `data` | C | Data package có sẵn, loader chưa có |
| `ai` | B | Provider, prompt, schema validator và safe fallback đã test |
| `core` | D | Mới có package skeleton |
| `rules` | D | Mới có package skeleton |
| `cli` | B | Shell, renderer, runtime port và lệnh terminal đã test |
| `tests` | B | 37 test pass, 1 live smoke skip; có unit/integration/eval fixture | Chưa có live model eval |

Chỉ nâng điểm khi có lệnh xác minh và artifact cụ thể; không nâng điểm dựa trên code chưa chạy.
