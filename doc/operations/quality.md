# Snapshot chất lượng VNeGuide

Thang điểm: A đầy đủ và ổn định; B hoạt động nhưng còn thiếu nhỏ; C hoạt động một phần; D chưa triển khai hoặc baseline hỏng.

## Domain sản phẩm

| Domain | Điểm | Bằng chứng | Khoảng trống chính |
| --- | --- | --- | --- |
| Procedure catalog | A | Repository audit, schema và checksum | Chưa kiểm tra freshness tự động |
| Source grounding | A | Source/status/procedure/local-path gate có unit test | Chưa tự refresh nguồn online |
| Structured extraction | B | Mock/OpenAI adapter, strict schema và unit test | Chưa có live model accuracy |
| Conversation flow | D | Chưa có implementation | Thiếu state machine nhiều lượt |
| Rule validation | C | Rule và context input có contract/audit | Chưa có Python rule handlers |
| Terminal chatbot | C | Có entrypoint, renderer và integration test | Thiếu core session factory |

## Module kiến trúc

| Module | Điểm | Trạng thái |
| --- | --- | --- |
| `domain` | B | Contract bất biến và unit test pass |
| `data` | B | Loader/repository/audit và unit test pass |
| `ai` | B | Provider, prompt, schema validator và safe fallback đã test |
| `core` | D | Mới có package skeleton |
| `rules` | D | Mới có package skeleton |
| `cli` | B | Shell, renderer, runtime port và lệnh terminal đã test |
| `tests` | B | Unit/integration/eval fixture; live model smoke còn skip |

Chỉ nâng điểm khi có lệnh xác minh và artifact cụ thể.
