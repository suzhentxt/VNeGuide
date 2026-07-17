# Snapshot chất lượng VNeGuide

Thang điểm: A đầy đủ và ổn định; B hoạt động nhưng còn thiếu nhỏ; C hoạt động một phần; D chưa triển khai hoặc baseline hỏng.

## Domain sản phẩm

| Domain | Điểm | Bằng chứng | Khoảng trống chính |
| --- | --- | --- | --- |
| Procedure catalog | A | Repository audit, schema và checksum | Chưa kiểm tra freshness tự động |
| Source grounding | A | Source/status/procedure/local-path gate có unit test | Chưa tự refresh nguồn online |
| Structured extraction | B | Mock/OpenAI adapter, strict schema và unit test | Chưa có live model accuracy |
| Conversation flow | B | Suggestion lifecycle, revision guard và retry cap có unit test | Chưa có web adapter |
| Rule validation | B | 27 handler và toàn bộ gold validation pass | Chưa có production monitoring |
| Terminal chatbot | B | Entry point nạp core factory và smoke test pass | Mock rỗng chỉ trả safe fallback |

## Module kiến trúc

| Module | Điểm | Trạng thái |
| --- | --- | --- |
| `domain` | B | Contract bất biến và unit test pass |
| `data` | B | Loader/repository/audit và unit test pass |
| `ai` | B | Provider, prompt, schema validator và safe fallback đã test |
| `core` | B | Multi-turn session và Accept/Reject/Edit đã test |
| `rules` | B | Deterministic handlers, missing fields và questions đã test |
| `cli` | B | Shell, renderer, runtime port và lệnh terminal đã test |
| `tests` | B | 75 pass, 1 live smoke skip; coverage 82.64% |

Chỉ nâng điểm khi có lệnh xác minh và artifact cụ thể.
