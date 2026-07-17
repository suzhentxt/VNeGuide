# AI

Owner: Người 2.

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
- `unsupported` là kết luận ngữ nghĩa; timeout/malformed/refusal trả `status="fallback"`,
  `procedure_code=None` và fields rỗng.
- Mọi call provider nhận JSON Schema strict. Unit test dùng `MockLLMProvider`, không cần key.
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
```

Adapter OpenAI dùng Responses API chính thức qua HTTPS và giữ allowlist
`api.openai.com/v1/responses`. Adapter LiteLLM dùng base URL do operator cấu hình, tự nối
`/v1/chat/completions`, gửi strict JSON Schema và có thể tắt Qwen thinking bằng
`chat_template_kwargs.enable_thinking=false`. Cả hai dùng thư viện chuẩn, chặn redirect và không
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
- Catalog chưa có metadata alias/evidence semantics đã review. Validator hiện bảo đảm evidence là
  đoạn xuất hiện trong message và kiểm type/enum/pattern/bounds cục bộ; nó chưa thể chứng minh tổng
  quát ý nghĩa enum/boolean hoặc xử lý phủ định. Không hard-code từ điển nghiệp vụ song song trong AI.
- `tests/evals/intent_cases.jsonl` là ground truth và contract fixture chạy qua scripted mock; chưa
  phải số đo accuracy của model thật. Live eval cần model/key riêng và không được log dữ liệu cá nhân.
