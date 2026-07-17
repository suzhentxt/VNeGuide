# Bàn giao phiên

## Trạng thái hiện tại

- Repo có data package v2, shared domain/data foundation, AI extraction, rule engine, conversation
  core và CLI shell.
- `vneguide.core:create_session` đã tồn tại và là factory mặc định của CLI.
- Core hỗ trợ suggestion, Accept/Reject/Edit, validation và question selection.
- AI hỗ trợ mock, OpenAI Responses và LiteLLM Chat Completions.
- Provider-only smoke đọc `.env` được chỉ định; composition root của CLI hiện đọc process
  environment, không tự nạp `.env`.

## Việc đã xác minh

- Working tree kết hợp: compileall, Ruff, formatter và Mypy pass.
- Pytest `87 passed, 1 skipped`; coverage `80.82%`.
- Terminal mock smoke nạp `vneguide.core:create_session` và `/quit` an toàn.
- Nhánh core/rules nguồn: Ruff/Mypy pass; Pytest `75 passed, 1 skipped`; coverage `82.64%`.
- LiteLLM trước merge: Pytest `74 passed, 1 skipped`; AI Ruff/format/Mypy pass.
- Provider-only smoke gọi thật `Qwen/Qwen3.5-9B` và nhận structured output tối thiểu; request không
  chứa catalog hoặc PII.

## Rủi ro

- Tài liệu Product/Architecture/Terminal cũ có thể mô tả phạm vi khác data package v2.
- Live provider connectivity không chứng minh accuracy của extraction hoặc full conversation.
- LiteLLM gateway hiện là public IP qua HTTP; key, prompt và response không có TLS. Chỉ dùng dữ
  liệu giả cho tới khi có HTTPS.
- CLI chưa ánh xạ câu lệnh người dùng sang `accept_suggestion`, `reject_suggestion` và
  `edit_suggestion`; web/widget adapter cần sở hữu interaction này.
- AI extraction chưa tạo 10 rule-context signal từ `rule_context_catalog.json`; các handler dùng
  document/context signal chưa thể nhận đủ dữ liệu từ hội thoại.
- 17/27 rule chưa có positive/triggering gold case riêng; test hiện chứng minh handler tồn tại và
  12 gold case hiện có pass, không chứng minh đủ hành vi của mọi handler.
- Một số rule dùng context/document signal, không được suy đoán từ field biểu mẫu.
- Git LFS có thể cần quyền ghi `.git/lfs/tmp` trong sandbox.

## Bước tốt nhất tiếp theo

Bổ sung adapter interaction hiển thị suggestion ID và gọi đúng Accept/Reject/Edit; đồng thời nối
rule-context signal vào extraction/core. Chạy lại terminal end-to-end bằng dữ liệu tổng hợp trước
khi nối web/widget.

## Lệnh

- Cài dev dependencies: `python -m pip install -e ".[dev]"`
- Ruff: `python -m ruff check .`
- Format: `python -m ruff format --check .`
- Type check: `python -m mypy`
- Test: `python -m pytest`
- Provider smoke: `python -m vneguide.ai.smoke --env-file .env --confirm-live`
- CLI: `python -m vneguide.cli`
