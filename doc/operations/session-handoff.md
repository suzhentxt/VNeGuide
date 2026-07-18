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
- Agent giữ compact memory theo session bằng mã thủ tục đang làm và field đang chờ; raw transcript và
  draft value không được gửi lại sang model ở lượt sau.
- Branch `agent/memory-form-sync` đã có draft response đầy đủ, manual field-edit API với optimistic
  revision, route-context seeding và `asked_question_ids`; form edit là `confirmed + dirty`. Create/GET
  session trả top-level draft snapshot để web hydrate ngay cả trước chat turn.

## Việc đã xác minh

- Python 3.11.9 trên working tree hiện tại: Compileall, Ruff lint/format và Mypy strict pass;
  Pytest `154 passed, 1 skipped`, coverage `82.50%`.
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
- Live multi-turn API → LiteLLM pass cho cả tạm trú và bản sao khai sinh: context sống qua small talk
  và câu trả lời ngắn, `submission_channel=online` được map đúng, không suy diễn “tôi/con tôi” thành tên.
- Test mới gồm 22 case multi-turn, 15 case form-sync API, 2 case race DELETE/TTL, 3 case grounding
  và 3 case core cho `NaN/Infinity`: stale revision không mutation, GET recovery, reset sạch, invalid
  field/type/enum/blank/non-finite, pending suggestion bị manual edit vô hiệu hóa và câu mơ hồ không
  tạo enum/name suy diễn.

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
- Compact memory mất khi API restart hoặc session hết TTL; đây chưa phải long-term/persistent memory.
- Frontend chưa có BFF/form binding cho endpoint field-edit mới; Người 1 cần thêm proxy dùng cookie
  `HttpOnly`, đồng bộ `draft.values` và bỏ response có revision thấp hơn state form hiện tại.
- `draft.revision` chỉ là optimistic token của form/suggestion; message retry dùng `client_turn_id`.
  Không dùng draft revision làm transcript revision nếu chưa mở rộng contract riêng.
- `npm audit --omit=dev` hiện báo 12 advisory production, gồm 4 mức high (trong đó có Next.js và
  dependency gián tiếp). Không deploy Internet trước khi nâng dependency có review và chạy lại gate.

## Bước tốt nhất tiếp theo

Người 1 nối form vào draft contract mới qua BFF, xử lý `stale_revision` bằng GET recovery và chạy hero
tạm trú 5/5. Sau đó Release Captain chạy E2E, nâng dependency web để xử lý advisory rồi audit/deploy.
Tiếp tục chỉ dùng LiteLLM HTTP cho smoke dữ liệu giả; không gửi PII hoặc hồ sơ thật trước khi gateway
có HTTPS.

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
- CLI: `python -m vneguide.cli`
