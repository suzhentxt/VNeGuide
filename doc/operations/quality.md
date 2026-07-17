# Snapshot chất lượng VNeGuide

Thang điểm: A đầy đủ và ổn định; B hoạt động nhưng còn khoảng trống; C mới hoạt động một phần;
D chưa triển khai hoặc baseline hỏng.

## Domain sản phẩm

| Domain | Điểm | Bằng chứng | Khoảng trống chính |
| --- | --- | --- | --- |
| Procedure catalog | A | Repository audit, schema và checksum | Chưa kiểm tra freshness tự động |
| Source grounding | A | Source/status/procedure/local-path gate có unit test | Chưa tự refresh nguồn online |
| Structured extraction | B | Mock/OpenAI/LiteLLM, strict schema, unit test và provider smoke | Chưa đo live accuracy |
| Conversation flow | B | Suggestion lifecycle, revision guard và retry cap có unit test | Chưa có web adapter |
| Rule validation | B | Đủ 27 handler; 12 gold case pass và kích hoạt 10 rule | 17 rule chưa có positive gold case; context chưa đi từ hội thoại vào core |
| Terminal chatbot | C | CLI nạp core factory và mock smoke pass | Chưa render/gọi Accept/Reject/Edit nên có thể kẹt ở suggestion |

## Module kiến trúc

| Module | Điểm | Trạng thái |
| --- | --- | --- |
| `domain` | B | Shared contract bất biến và unit test |
| `data` | B | Loader/repository/audit và checksum gate |
| `ai` | B | Provider, prompt, validator, fallback và LiteLLM smoke |
| `core` | B | Multi-turn session và suggestion lifecycle |
| `rules` | B | Deterministic handlers, missing fields và question selector |
| `cli` | B | Shell, renderer, runtime port và core factory |
| `tests` | B | Unit/integration/eval fixtures; live session vẫn opt-in |

## Quality gate

- Working tree kết hợp: compileall, Ruff, formatter và Mypy pass; Pytest
  `87 passed, 1 skipped`; coverage `80.82%`.
- Gate LiteLLM trước merge: Pytest `74 passed, 1 skipped`; Ruff/format/Mypy pass cho AI và test
  liên quan; provider-only live smoke pass.
- Gate core/rules trên nhánh nguồn: Ruff/Mypy pass; Pytest `75 passed, 1 skipped`; coverage `82.64%`.

Terminal mock smoke đã nạp `vneguide.core:create_session` và xử lý `/quit` an toàn. Provider
connectivity smoke không được coi là bằng chứng accuracy model hoặc hội thoại nghiệp vụ end-to-end.
