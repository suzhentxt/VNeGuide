# Bàn giao phiên

## Trạng thái hiện tại

- Repo đã có cấu trúc module và data package v2.
- Scope runtime nằm trong `data/README.md`.
- CLI shell, renderer, integration port và quality tooling đã được triển khai.
- `python -m vneguide.cli` đã là entry point hợp lệ nhưng chưa xử lý hội thoại vì core chưa cung cấp `vneguide.core:create_session`.
- `src/vneguide/ai/` đã có provider interface, mock/OpenAI adapter, catalog-derived prompt/schema,
  structured validator, bounded retry và safe fallback.
- Chưa có domain model, data loader hoặc conversation orchestrator.
- Runtime local hiện là Python 3.11.14; CLI trước đó cũng đã được xác minh trên Python 3.12.7.

## Việc đã xác minh

- JSON và JSONL trong data package parse được.
- Các nguồn local được đăng ký đều tồn tại.
- Sau khi rebase AI lên CLI mới nhất, Ruff lint/format đúng scope và Mypy strict đều đạt.
- Full Pytest đạt `37 passed, 1 skipped`; `compileall` đạt.
- Riêng extractor trước rebase đạt 28 test và 41 subtest bằng scripted mock/fake transport.
- Test AI không cần API key; OpenAI REST behavior được kiểm bằng fake HTTP transport.
- Repo không còn conflict marker sau lần kiểm tra gần nhất.

## Rủi ro

- Tài liệu Product/Architecture/Terminal cũ vẫn mô tả bộ thủ tục khác data package v2.
- `ExtractionOutcome` và wire shape trong `ai` là contract nội bộ tạm thời, không phải shared/frozen
  domain contract. Người 1 cần cung cấp model và loader trước khi tích hợp với core.
- Catalog chưa có alias/evidence semantics đã review. Validator chỉ chứng minh evidence xuất hiện
  trong message và kiểm constraint cục bộ; không thể tổng quát xác minh enum/boolean, vai trò hoặc
  phủ định. Không thêm từ điển nghiệp vụ song song vào AI.
- Fixture intent dùng scripted mock nên chỉ kiểm contract/pipeline, không chứng minh accuracy model.
- Chưa chạy live OpenAI smoke/eval trong phiên này vì không sử dụng API key.
- Freshness `next_review_at`, source governance và business validation thuộc data/domain/rules,
  không được chuyển vào extractor.
- Git LFS có thể cần quyền ghi `.git/lfs/tmp` trong môi trường sandbox.
- Live provider smoke test đang skip và chưa có bằng chứng gọi model thật.

## Bước tốt nhất tiếp theo

Người 1 tạo domain contract và data loader từ package hiện hành. Sau đó thay direct data-package
loading trong AI bằng loader, map kết quả sang domain model và giao Người 3 tích hợp qua adapter đó.
Khi có credentials được quản lý an toàn, thêm live eval harness để đo intent/slot accuracy mà không
log prompt/output chứa PII.

## Lệnh dự kiến

- Cài dev dependencies: `python -m pip install -e ".[dev]"`
- Quality gate: `python -m ruff check .`, `python -m mypy`, `python -m pytest`
- Unit AI không cần dependency ngoài: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests/unit -v`
- Lint/format riêng phần AI: `ruff check src/vneguide/ai tests/unit/test_extractor.py` và
  `ruff format --check src/vneguide/ai tests/unit/test_extractor.py`
- CLI: `python -m vneguide.cli`

Các lệnh quality gate đã được xác minh sau rebase. CLI hiện trả thông báo cấu hình an toàn cho đến
khi `vneguide.core:create_session` được triển khai.
