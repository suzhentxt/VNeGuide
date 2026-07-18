# Bàn giao phiên

## Trạng thái hiện tại

- Repo có data package v2, domain/data runtime foundation, AI extraction, deterministic rule engine,
  suggestion-aware conversation core và CLI shell.
- Scope runtime được khóa bởi `data/README.md`; `vneguide.domain` cung cấp contract dùng chung và
  `ProcedureRepository` cung cấp dữ liệu đã audit.
- `vneguide.core:create_session` là factory mặc định của CLI; core/rules hỗ trợ suggestion,
  Accept/Reject/Edit, validation và question selection.
- AI hỗ trợ mock, OpenAI Responses và LiteLLM Chat Completions. Provider-only smoke đọc `.env` được
  chỉ định; HTTP API hỗ trợ opt-in `--env-file .env`, còn các luồng khác chỉ đọc process environment
  trừ khi `VNEGUIDE_LLM_ENV_FILE` được đặt tường minh.
- Repo có FastAPI Chat API, Next.js BFF và chatbox chỉ mount trong
  `/hon-nhan-va-gia-dinh/**`.
- Repo có thêm `demoweb/`, một giao diện Next.js độc lập; thư mục này không phụ thuộc tool clone hoặc dữ liệu capture ban đầu.
- Luồng Hôn nhân và gia đình trong `demoweb` đã sửa catalog, lựa chọn dịch vụ/đơn vị, form không điền sẵn PII và tải cơ quan có timeout/thử lại.
- Session web dùng cookie `HttpOnly`; Python store hiện là in-memory single-process với TTL/capacity/per-session lock.
- Nhánh Người 4 có adapter/worker Qwen OCR cho CT01 tại `src/vneguide/ocr/`; output chỉ là candidate
  `USER_UPLOAD`, chưa nối trực tiếp vào core/api/demoweb để giữ đúng module owner.

## Việc đã xác minh

- Python 3.11.9 trên working tree hợp nhất: Compileall, Ruff lint/format và Mypy strict pass;
  Pytest `91 passed, 1 skipped`, coverage `80.64%`.
- Terminal mock smoke nạp `vneguide.core:create_session` và `/quit` an toàn, không gọi provider
  ngoài.
- `demoweb`: `npm run check` pass; ESLint, TypeScript và production build đủ 29 route, gồm ba BFF
  route `/api/chat/*`.
- Test Python hiện bao gồm FastAPI session/message/suggestion flow, session store và toàn bộ
  LiteLLM/core/rules test trước đó.
- Provider-only smoke trước merge đã gọi thật `Qwen/Qwen3.5-9B` và nhận structured output tối thiểu;
  request chỉ chứa schema tổng hợp, không chứa catalog hoặc PII.
- Bằng chứng trên nhánh nguồn: local web → BFF → Python API pass với mock rỗng; 12 HTTP assertion
  production cho catalog, tìm kiếm, lựa chọn, redirect và API validation đều pass.
- Live web BFF → Python API → LiteLLM pass bằng dữ liệu giả: session `201`, message `200`, nhận diện
  `1.004194` và có assistant response; không gửi PII hoặc hồ sơ thật.
- OCR gate: Ruff/format/Mypy pass; toàn repo `127 passed, 1 skipped`. Live OCR smoke 3 lượt fixture
  CT01 giả đạt field recall `0.75`, latency trung bình `6,688` giây và cố ý báo không đạt vì chưa ổn
  định 4/4 field.

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
- Git LFS có thể cần quyền ghi `.git/lfs/tmp` trong môi trường sandbox.
- Danh sách Phường/Xã và Sở phụ thuộc upstream `vpcp.dichvucong.gov.vn`; khi upstream lỗi hoặc quá hạn, UI hiển thị lỗi và cho phép thử lại thay vì dùng dữ liệu giả.
- Bốn mã đang hoạt động trên web (`1.000894`, `2.000806`, `1.004859`, `2.000748`) chưa có procedure pack backend; chat hiển thị scope warning và chưa thể kết luận nghiệp vụ cho các mã này.
- In-memory session store chỉ phù hợp một API worker; cần Redis hoặc store dùng chung trước khi scale nhiều worker.
- Gateway trong `.env` dùng HTTP nên ảnh không được mã hóa trên đường truyền; tuyệt đối không gửi CT01
  hoặc PII thật cho tới khi có HTTPS. Qwen OCR hiện chưa ổn định 4/4 field và phải luôn có nhập tay.
- `npm audit --omit=dev` hiện báo 12 advisory production, gồm 4 mức high (trong đó có Next.js và
  dependency gián tiếp). Không deploy Internet trước khi nâng dependency có review và chạy lại gate.

## Bước tốt nhất tiếp theo

Trước khi deploy, nâng dependency web để xử lý advisory rồi chạy lại `npm run check` và audit. Tiếp
theo, review/bổ sung data package cho bốn thủ tục Hôn nhân và gia đình, nối 10 rule-context signal vào
extraction/core và hoàn thiện CLI để hiển thị suggestion ID, gọi đúng Accept/Reject/Edit. Chạy E2E
terminal/API/web bằng dữ liệu tổng hợp. Chỉ dùng LiteLLM HTTP cho smoke dữ liệu giả; không gửi PII
hoặc hồ sơ thật trước khi gateway có HTTPS.

Với OCR, bước tích hợp cụ thể là để Người 2/5 triển khai `OcrCandidateSink`, đưa candidate vào
suggestion `pending` kèm revision guard rồi hiển thị bằng Accept/Reject/Edit hiện có; không gọi method
ghi draft từ OCR. Người 5 cần thêm extra dependency Pillow/pypdfium2 trước khi merge.

## Lệnh

- Cài Python API: `python -m pip install -e ".[dev,api]"`
- Chạy API với model trong `.env`: `python -m vneguide.api --env-file .env`
- Chạy API bằng process environment/mock: `python -m vneguide.api`
- Chạy web: `cd demoweb`, `npm ci`, `npm run dev -- --hostname 0.0.0.0 -p 3000`
- Kiểm tra web: `cd demoweb`, `npm run check`
- Audit dependency production: `cd demoweb`, `npm audit --omit=dev`
- Cài dev dependencies: `python -m pip install -e ".[dev]"`
- Ruff: `python -m ruff check .`
- Format: `python -m ruff format --check .`
- Type check: `python -m mypy`
- Test: `python -m pytest`
- Provider smoke: `python -m vneguide.ai.smoke --env-file .env --confirm-live`
- OCR unit/eval: `python -m pytest tests/unit/test_ocr*.py tests/evals/test_ocr_ct01_acceptance.py`
- OCR live fixture: `python -m vneguide.ocr.smoke --env-file .env --runs 3 --confirm-live`
- CLI: `python -m vneguide.cli`
