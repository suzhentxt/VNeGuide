# Snapshot chất lượng VNeGuide

Thang điểm: A đầy đủ và ổn định; B hoạt động nhưng còn khoảng trống; C mới hoạt động một phần;
D chưa triển khai hoặc baseline hỏng.

## Domain sản phẩm

| Domain | Điểm | Bằng chứng | Khoảng trống chính |
| --- | --- | --- | --- |
| Procedure catalog | A | Repository audit, schema và checksum | Chưa kiểm tra freshness tự động |
| Source grounding | A | Source/status/procedure/local-path gate có unit test | Chưa tự refresh nguồn online |
| Structured extraction | B | Mock/OpenAI/LiteLLM, strict schema, unit test và provider smoke | Chưa đo live accuracy |
| Conversation flow | B | Suggestion lifecycle, revision guard, retry cap, web BFF và browser E2E | OCR upload UI chưa hoàn thành |
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

- Cây `dev` audit 2026-07-19: Ruff lint/format và Mypy strict pass; Pytest
  `305 passed, 2 skipped`; coverage `80.58%`.
- Release API integration: `12 passed`, gồm đúng ba mã, out-of-scope, hero 5/5, stale revision,
  edit/reset, typed timeout và generic OCR fallback.
- Web: `npm run check` pass với 22 unit test và 25 route; `npm audit --audit-level=moderate` báo 0
  vulnerability. Playwright đạt `15 passed, 1 skipped`; skip là OCR upload UI chưa tồn tại.
- Provider-only live smoke ở commit nguồn đã pass bằng fixture tổng hợp; chưa phải accuracy gate của
  artifact release và không thay thế browser E2E.

Terminal mock smoke đã nạp `vneguide.core:create_session` và xử lý `/quit` an toàn. Provider
connectivity smoke không được coi là bằng chứng accuracy model. Browser E2E mặc định dùng mock
provider để tái lập và không thay thế live-model evaluation.
