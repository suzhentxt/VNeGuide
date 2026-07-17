# Bàn giao phiên

## Trạng thái hiện tại

- Repo đã có cấu trúc module, data package v2 và domain/data runtime foundation.
- Scope runtime nằm trong `data/README.md`.
- `vneguide.domain` đã cung cấp enum, model và contract dùng chung.
- `ProcedureRepository` đã load/audit pack, catalog, source, rule context và checksum.
- Chưa có AI provider, rule engine thực thi, orchestrator hoặc CLI chạy được.
- Host vẫn chưa có Python; lần xác minh gần nhất dùng Python 3.11.9 embeddable tạm và đã xóa sau khi test.

## Việc đã xác minh

- Compile thành công 21 file Python.
- 25 unit test pass.
- Ba procedure pack, 44 field, 10 rule-context input, 27 rule và 13 source pass audit.
- 12 checksum pass theo chuẩn UTF-8/LF.
- Các nguồn runtime đều ở trạng thái `approved`, đúng procedure và file local nằm trong data root.
- Repo không còn conflict marker sau lần kiểm tra gần nhất.

## Rủi ro

- Tài liệu Product/Architecture/Terminal cũ vẫn mô tả bộ thủ tục khác data package v2.
- 17/27 validation rule chưa có positive gold case.
- Rule condition chưa phải DSL thực thi; theo OD-004 phải dùng handler xác định theo `rule_id`, không dùng `eval/exec`.
- `pytest`/`ruff` chưa nằm trong dependency và host chưa có Python để chạy lại lệnh chuẩn.
- Git LFS có thể cần quyền ghi `.git/lfs/tmp` trong môi trường sandbox.

## Bước tốt nhất tiếp theo

Tạo `LLMProvider` interface, mock provider và structured extraction dùng `ExtractionResult`; không định nghĩa lại `ProcedureCode`, `CaseDraft` hoặc field catalog trong module AI.

## Lệnh dự kiến

- Cài đặt sau khi có Python 3.11+: `py -m pip install -e .`
- Unit test không cần pytest: `$env:PYTHONPATH='src'; py -m unittest discover -s tests -v`
- Test pytest sau khi Người 4 bổ sung dev dependency: `py -m pytest`
- CLI mục tiêu: `py -m vneguide.cli`

Lệnh `unittest` đã được xác minh tương đương bằng Python 3.11.9 embeddable; các lệnh dùng `py` chưa chạy được vì host chưa cài interpreter.
