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
- AI có `ExtractionContext` cho procedure/field đang hỏi và schema riêng cho rule-context signal.
  Text extractor chỉ nhận signal `intent_extraction`/`user_declaration`; signal `document_check`
  phải đến từ OCR/document adapter đã validate. Signal text là candidate: rule engine yêu cầu ID đã
  confirm; document/derived signal yêu cầu ID được trusted adapter promote.
- Repo có FastAPI Chat API, Next.js BFF và chatbox chỉ mount trong
  `/hon-nhan-va-gia-dinh/**`.
- Repo có thêm `demoweb/`, một giao diện Next.js độc lập; thư mục này không phụ thuộc tool clone hoặc dữ liệu capture ban đầu.
- Luồng Hôn nhân và gia đình trong `demoweb` đã sửa catalog, lựa chọn dịch vụ/đơn vị, form không điền sẵn PII và tải cơ quan có timeout/thử lại.
- Session web dùng cookie `HttpOnly`; Python store hiện là in-memory single-process với TTL/capacity/per-session lock.

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
- Branch Người 3: Pytest `111 passed, 1 skipped`; Ruff lint/format, Mypy strict pass; coverage
  `80.80%`. Eval fixture có 21 case tổng hợp; runner live opt-in verify checksum trước provider call,
  nhưng chưa có metric model thật vì process hiện dùng provider `mock` và chưa cấu hình model.

## Rủi ro

- Tài liệu Product/Architecture/Terminal cũ có thể mô tả phạm vi khác data package v2.
- Live provider connectivity không chứng minh accuracy của extraction hoặc full conversation.
- LiteLLM gateway hiện là public IP qua HTTP; key, prompt và response không có TLS. Chỉ dùng dữ
  liệu giả cho tới khi có HTTPS.
- CLI chưa ánh xạ câu lệnh người dùng sang `accept_suggestion`, `reject_suggestion` và
  `edit_suggestion`; web/widget adapter cần sở hữu interaction này.
- AI extraction đã có contract riêng cho signal extractable, nhưng core chưa truyền
  `ExtractionContext` hoặc lưu candidate/evidence/confirmation/trusted-adapter provenance vào
  conversation state; runtime web vì vậy chưa dùng được phần mới cho đến khi Người 2 nối adapter.
- Signal `requested_variant` là string chưa có canonical values trong catalog nên bị giữ khỏi text
  model; dùng enum `intent` cho routing khai sinh cho tới khi Domain/Data review constraint.
- 17/27 rule chưa có positive/triggering gold case riêng; test hiện chứng minh handler tồn tại và
  12 gold case hiện có pass, không chứng minh đủ hành vi của mọi handler.
- Sáu case `gold_validation` chưa thống nhất nghĩa `source_ids` với runtime; OD-005 giữ default an
  toàn và không thay ground truth chỉ để test pass.
- `ValidationResult.ready_to_submit` hiện chỉ phản ánh rule không kích hoạt; một số gold case vẫn kỳ
  vọng trạng thái này khi thiếu required field. Core có chặn `NextAction.COMPLETE` bằng
  `missing_fields`, nhưng web vẫn có thể hiển thị đồng thời READY và danh sách thiếu. OD-006 yêu cầu
  Domain/Core/API/UI khóa semantics trước khi sửa status/ground truth hoặc hiển thị “sẵn sàng nộp”.
- Một số rule dùng context/document signal, không được suy đoán từ field biểu mẫu.
- Git LFS có thể cần quyền ghi `.git/lfs/tmp` trong môi trường sandbox.
- Danh sách Phường/Xã và Sở phụ thuộc upstream `vpcp.dichvucong.gov.vn`; khi upstream lỗi hoặc quá hạn, UI hiển thị lỗi và cho phép thử lại thay vì dùng dữ liệu giả.
- Bốn mã đang hoạt động trên web (`1.000894`, `2.000806`, `1.004859`, `2.000748`) chưa có procedure pack backend; chat hiển thị scope warning và chưa thể kết luận nghiệp vụ cho các mã này.
- In-memory session store chỉ phù hợp một API worker; cần Redis hoặc store dùng chung trước khi scale nhiều worker.
- `npm audit --omit=dev` hiện báo 12 advisory production, gồm 4 mức high (trong đó có Next.js và
  dependency gián tiếp). Không deploy Internet trước khi nâng dependency có review và chạy lại gate.

## Bước tốt nhất tiếp theo

Người 2 cần đổi extractor protocol để truyền `ExtractionContext` từ procedure/field thực sự đang hỏi,
đồng thời thêm state riêng cho `context_signals`, evidence và promotion IDs; API không được nhận
origin/confirmation/trust trực tiếp từ client. Người 1/API serializer cần ẩn hoặc đổi nhãn READY khi
`missing_fields` chưa rỗng cho tới khi OD-006 được khóa. Sau đó cấu hình provider/model/key cục bộ và
chạy live evaluator bằng fixture tổng hợp. Trước khi
deploy Internet vẫn phải nâng dependency web, chạy lại `npm run check`/audit và chỉ dùng LiteLLM HTTP
cho dữ liệu giả cho tới khi gateway có HTTPS.

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
- Live extraction metrics: `python -m tests.evals.run_live_extraction_eval --confirm-live --env-file .env --output C:\tmp\vneguide-extraction-eval.json`
- CLI: `python -m vneguide.cli`
