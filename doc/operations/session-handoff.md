# Bàn giao phiên

## Trạng thái hiện tại

- Repo đã có data package v2, shared domain contract, data repository, AI extraction và CLI harness.
- Scope runtime nằm trong `data/README.md`.
- `vneguide.domain` cung cấp enum/model/contract dùng chung.
- `ProcedureRepository` load/audit pack, catalog, source, rule context và checksum.
- `src/vneguide/ai/` có mock/OpenAI adapter, catalog-derived prompt/schema, bounded retry và fallback.
- `python -m vneguide.cli` đã có entry point nhưng còn chờ `vneguide.core:create_session`.
- Deterministic rule handlers và conversation orchestrator chưa được triển khai.

## Việc đã xác minh cho trạng thái hợp nhất hiện tại

- Domain/data: compile 21 file, 25 unit test pass.
- Data audit: ba pack, 44 field, 10 rule-context input, 27 rule, 13 source và 12 checksum pass.
- AI + CLI trên `main`: Ruff/Mypy/compileall pass; Pytest `37 passed, 1 skipped`.
- OpenAI adapter dùng fake transport; chưa gọi model thật hoặc đo live accuracy.
- Sau resolve conflict: compile toàn bộ 42 file Python thành công; unittest discovery chạy 63 test,
  đạt `62 passed, 1 skipped` (live provider smoke test là opt-in).
- Ruff, formatter, Mypy và Pytest chưa chạy lại vì Python embeddable tạm không có dev dependencies.

## Rủi ro

- Tài liệu Product/Architecture/Terminal cũ vẫn mô tả bộ thủ tục khác data package v2.
- AI còn `ExtractionOutcome`/provider-facing models nội bộ; cần adapter rõ ràng sang shared domain.
- 17/27 validation rule chưa có positive gold case.
- Rule condition chưa phải DSL; theo OD-004 phải dùng handler theo `rule_id`, không `eval/exec`.
- Evidence validation cục bộ không chứng minh được toàn bộ ngữ nghĩa phủ định/vai trò.
- Live provider smoke test đang skip và chưa có bằng chứng gọi model thật.
- Git LFS có thể cần quyền ghi `.git/lfs/tmp` trong sandbox.

## Bước tốt nhất tiếp theo

Người 3 triển khai rule handlers và `vneguide.core:create_session`, dùng shared `CaseDraft`,
`ConversationState`, `TurnRequest` và `TurnResult`. AI output phải đi qua adapter sang
`ExtractionResult`; không cho CLI hoặc AI sở hữu business rule.

## Lệnh

- Cài dev dependencies: `python -m pip install -e ".[dev]"`
- Quality gate: `python -m ruff check .`
- Format check: `python -m ruff format --check .`
- Type check: `python -m mypy`
- Test: `python -m pytest`
- Unit test không cần pytest: `python -m unittest discover -s tests -v`
- CLI: `python -m vneguide.cli`
