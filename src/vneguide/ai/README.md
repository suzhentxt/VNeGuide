# AI

Owner theo kế hoạch `chiaviec.md`: Người 3.

Module này chỉ phân loại ngôn ngữ và trích xuất dữ liệu người dùng đã nêu. Nó không quyết
định required field, checklist, phí, thời hạn, trạng thái hồ sơ hoặc `source_id`.

```text
config.py          # Đọc cấu hình provider khi được gọi; không đọc secret lúc import
extractor.py       # Retry có giới hạn và fallback kỹ thuật an toàn
schemas.py         # Sinh/validate schema output từ data package đã review
prompts/           # Prompt contract thuần routing và extraction
providers/         # Interface, mock, OpenAI Responses và LiteLLM Chat Completions
```

## Contract

- Routing dùng procedure code trong `data/catalog/`, không dùng enum trích lục cũ trong tài
  liệu Terminal.
- Field/type/enum được nạp từ `data/catalog/field_catalog.json`; không có bản sao field list
  trong source.
- Mỗi field do model trả về phải có evidence nguyên văn trong tin nhắn hiện tại.
- `ExtractionTurnContext` chỉ mang `active_procedure_code`, `expected_field_id` và cờ
  `confirmation_required` để hiểu câu trả lời ngắn hoặc một thủ tục đang chờ xác nhận. Context không
  chứa lịch sử và không được dùng làm evidence.
- Rule-context signal được tách khỏi field biểu mẫu. Text model chỉ được sinh signal có origin
  `intent_extraction` hoặc `user_declaration`; signal `document_check` chỉ đến từ adapter tài liệu.
  Các signal từ text vẫn là candidate chưa xác nhận: `origin` mô tả loại nguồn theo catalog, không
  phải bằng chứng tin cậy để kích hoạt rule.
- `unsupported` là kết luận ngữ nghĩa; timeout/malformed/refusal trả `status="fallback"`,
  `procedure_code=None` và fields rỗng.
- Mọi call provider nhận JSON Schema strict. Unit test dùng `MockLLMProvider`, không cần key.
- Trước structured extraction, `vneguide.language` chuẩn hóa phương ngữ/ASR theo glossary đã review,
  bảo vệ dữ liệu định danh và remap evidence từ câu chuẩn hóa về đúng câu gốc. Tầng model-assisted
  mặc định tắt và không chứa bảng phương ngữ trong prompt.
- `ExtractionOutcome` hiện là contract nội bộ của module AI. Chỉ map sang contract dùng chung sau
  khi `src/vneguide/domain/` có model chính thức; không dùng class này để khóa domain contract.

Ví dụ khởi tạo catalog từ repo:

```python
from pathlib import Path

from vneguide.ai import (
    ExtractionCatalog,
    StructuredExtractor,
    build_llm_provider,
    load_llm_config,
)

catalog = ExtractionCatalog.from_data_package(Path("data"))
provider = build_llm_provider(load_llm_config())
extractor = StructuredExtractor(provider, catalog)

from vneguide.ai import ExtractionTurnContext

outcome = extractor.extract(
    "Cho bản thân tôi",
    context=ExtractionTurnContext(
        active_procedure_code="1.004194",
        expected_field_id="registration_mode",
    ),
)
```

Adapter OpenAI dùng Responses API chính thức qua HTTPS và giữ allowlist
`api.openai.com/v1/responses`. Adapter LiteLLM dùng base URL do operator cấu hình, tự nối
`/v1/chat/completions`, gửi strict JSON Schema và có thể tắt Qwen thinking bằng
`chat_template_kwargs.enable_thinking=false`; extraction dùng `temperature=0`. Cả hai dùng thư viện
chuẩn, chặn redirect và không
log prompt, raw output hoặc key.

Smoke trực tiếp AI layer bằng một input tổng hợp, không cần `vneguide.core:create_session`:

```powershell
python -m vneguide.ai.smoke --env-file .env --confirm-live
```

HTTP custom endpoint bị từ chối nếu chưa bật `VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=1`. Cờ này chỉ
dành cho gateway dev tin cậy; terminal chứa dữ liệu người dùng thật phải đi qua HTTPS.

## Giới hạn tích hợp hiện tại

- `src/vneguide/data/` đã có `ProcedureRepository`. Composition root của core dùng repository để
  khám phá data root; adapter extraction hiện vẫn dựng schema bằng `ExtractionCatalog` từ cùng data
  package đã audit, không duy trì bản sao field list trong source.
- Catalog chưa có metadata evidence semantics đầy đủ. Validator bảo đảm evidence là đoạn xuất hiện
  trong message và kiểm type/enum/pattern/bounds cục bộ. Với boolean rule-context, validator còn
  đối chiếu từ khóa từ label đã review và kiểm polarity trên cả evidence lẫn mệnh đề trong toàn bộ
  current message để model không thể cắt bỏ `không/chưa`. Enum/boolean tổng quát vẫn là candidate
  cần Accept/Edit; không hard-code từ điển nghiệp vụ song song trong AI.
- `tests/evals/intent_cases.jsonl` là contract fixture chạy qua scripted mock, không phải số đo
  accuracy. Live evaluator trong `tests/evals/run_live_extraction_eval.py` chỉ chạy khi operator chủ
  động cấu hình provider/model; báo metric và metadata nhưng không đọc hoặc in API key.
