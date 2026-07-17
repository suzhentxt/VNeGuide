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
| Structured extraction | B | Mock/OpenAI adapter, strict schema và unit test | Chưa map hoàn toàn sang shared domain; chưa đo live accuracy |
| Conversation flow | D | Chưa có implementation | Thiếu state machine nhiều lượt |
| Rule validation | C | 27 rule và 10 context input có contract/audit | Chưa có Python handler; thiếu 17 positive cases |
| Terminal chatbot | C | Có entry point, renderer và integration test | Chưa chạy hội thoại end-to-end vì thiếu core |

## Module kiến trúc

| Module | Điểm hiện tại | Trạng thái |
| --- | --- | --- |
| `domain` | B | Contract bất biến và unit test pass |
| `data` | B | Loader/repository/audit và unit test pass |
| `ai` | B | Provider, prompt, schema validator và safe fallback đã test |
| `core` | D | Mới có package skeleton |
| `rules` | D | Mới có package skeleton |
| `cli` | B | Shell, renderer, runtime port và lệnh terminal đã test |
| `tests` | B | Có unit/integration/eval fixture; live smoke còn skip |

Chỉ nâng điểm khi có lệnh xác minh và artifact cụ thể. Sau merge ngày 2026-07-17, compile toàn bộ
42 file Python thành công và unittest discovery đạt `62 passed, 1 skipped`; Ruff, formatter, Mypy
và Pytest chưa chạy lại vì runtime tạm không cài dev dependencies.
