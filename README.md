# VNeGuide Terminal MVP

VNeGuide là chatbot hỗ trợ người dân chuẩn bị và kiểm tra trước hồ sơ dịch vụ công. Phạm vi runtime hiện hành được khóa bởi [`data/README.md`](data/README.md) và gồm:

- `2.000635`: Cấp bản sao Trích lục hộ tịch — bản sao Giấy khai sinh.
- `1.013314`: Xác nhận điều kiện diện tích bình quân nhà ở và tình trạng chỗ ở.
- `1.004194`: Đăng ký tạm trú.

Các tài liệu sản phẩm cũ trong `doc/` phải được đối chiếu với data package trước khi dùng để code. VNeGuide chỉ hỗ trợ hướng dẫn, kiểm tra và chuẩn bị hồ sơ; kết quả không phải quyết định hành chính.

## Yêu cầu

- Python 3.11 trở lên.
- Không cần API key khi dùng mock provider và chạy test mặc định.
- API key cần cho mọi luồng dùng provider thật, gồm CLI, HTTP API và live smoke chủ động.

## Cài đặt

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[api,dev,ocr]"
Copy-Item .env.example .env
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[api,dev,ocr]'
cp .env.example .env
```

`.env` đã được Git bỏ qua. Runtime không đọc secret lúc import. Lệnh smoke provider và HTTP API chỉ
đọc file khi được chỉ định rõ bằng `--env-file`; các luồng khác vẫn nhận cấu hình từ environment.
File mẫu mặc định dùng `mock`; chỉ đổi sang LiteLLM/OpenAI khi đã có endpoint HTTPS và secret hợp lệ.

## Chạy chatbot

Lệnh thống nhất:

```powershell
python -m vneguide.cli
```

CLI nạp session factory từ `VNEGUIDE_SESSION_FACTORY`, mặc định là `vneguide.core:create_session`. Factory do lớp tích hợp core cung cấp và phải trả về session có phương thức `send(message) -> TurnResult`. Thiết kế này giữ CLI độc lập với LLM, rule engine và state machine.

Các lệnh trong phiên:

- `/status`: in lại trạng thái hồ sơ gần nhất.
- `/reset`: hủy state hiện tại và tạo session mới.
- `/quit`: đóng session và thoát.

Mỗi lượt hiển thị câu trả lời, thủ tục nhận diện, dữ liệu trích xuất, hồ sơ nháp, trường còn thiếu, lỗi validation, nguồn tham khảo và bước tiếp theo. Các field định danh phổ biến như `cccd` được che trước khi hiển thị.

Hook mặc định `vneguide.core:create_session` đã được triển khai. Với mock provider không có response dựng sẵn, core trả fallback an toàn; để hội thoại bằng model thật cần cấu hình provider/model/key theo phần bên dưới. CLI không chứa business logic của core.

Core mặc định dùng biến thể `guided`. Khi route đã khóa đúng một trong ba mã thủ tục, câu hỏi thuần
guidance như “Lệ phí bao nhiêu?” được trả trực tiếp trước structured extraction; chatbot vì vậy vẫn
trình bày được phí, thời gian, hồ sơ, các bước, cơ quan, kênh nộp và kết quả khi provider chậm hoặc
tạm thời không khả dụng. Matcher dùng whole-message allowlist; câu chứa field, thủ tục khác hoặc nội
dung hỗn hợp vẫn đi qua extractor. Nội dung được render từ procedure pack đã review và giữ
`source_id`; lớp này không đọc transcript/draft và không được thay đổi rule, revision hoặc suggestion.
Đặt `VNEGUIDE_CHAT_CORE_VARIANT=baseline` để rollback/A-B mà không đổi API.

## Chạy HTTP API và demoweb

Browser gọi Next.js BFF tại `/api/chat/*`; BFF giữ session ID trong cookie `HttpOnly` và gọi Python
API ở phía server. API key model không được đưa vào biến `NEXT_PUBLIC_*`.

Terminal 1 — chạy Python Chat API:

```powershell
.venv\Scripts\Activate.ps1
python -m vneguide.api --env-file .env
```

`--env-file` là opt-in tường minh cho local development; file chỉ được đọc các khóa LLM trong danh
sách cho phép. Có thể bỏ tùy chọn này khi provider/model/key đã được đặt trực tiếp trong process
environment.

Terminal 2 — chạy Next.js:

```powershell
Copy-Item demoweb\.env.local.example demoweb\.env.local
Set-Location demoweb
npm ci
npm run dev
```

Mặc định BFF gọi `http://127.0.0.1:8000`. Có thể đổi bằng `VNEGUIDE_API_BASE_URL` trong `demoweb/.env.local`. Kiểm tra API bằng `GET /health`.

Demoweb hiện chỉ hiển thị đúng ba thủ tục đã khóa trong `data/README.md`: `2.000635`, `1.013314` và
`1.004194`. Luồng đăng ký kết hôn cũ đã bị loại khỏi route hỗ trợ. Form sâu của `1.004194` dùng
shared workspace với chat. BFF `/api/chat/field` gọi endpoint backend revisioned; manual edit được
kiểm tra stale revision và đánh dấu field đã xác nhận/dirty.

Chatbot hỗ trợ hai luồng trên cùng một API: hỏi–đáp thông tin thủ tục và hỗ trợ điền form. Model chỉ
route mã thủ tục, topic và enum tham chiếu; `ProcedureQAResponder` dựng câu trả lời từ procedure pack
đã duyệt, không gọi model lần hai và không cho câu hỏi FAQ tự ghi vào form. FAQ đầu phiên sẽ trả lời,
sau đó hỏi người dùng có muốn thực hiện thủ tục hay không. Trong lúc điền form, FAQ giữ nguyên draft,
revision, suggestion và bước đang làm. Các topic hiện có gồm phí, thời gian, giấy tờ, thông tin cần
khai, cơ quan, kênh nộp, kết quả, các bước, căn cứ, điều kiện giới hạn và giải thích field.

## OCR kiểm tra tài liệu tạm trú

Module `vneguide.ocr` kiểm tra nhẹ giấy tờ chỗ ở hợp pháp và văn bản đồng ý của cha/mẹ/người giám hộ
tại bước 2 của thủ tục `1.004194`. Demoweb upload qua BFF tới worker riêng; OpenAI key và worker token
không đi xuống browser. OCR chỉ trả `pass`, `needs_review` hoặc `fail`, không trả raw text, không tự
điền draft và không kết luận giá trị pháp lý. Bản demo chỉ nhận tài liệu tổng hợp hoặc đã ẩn danh.
Xem contract, lệnh chạy và hai ảnh test tại
[`src/vneguide/ocr/README.md`](src/vneguide/ocr/README.md).

## Cấu hình provider

Các biến mẫu nằm trong `.env.example`:

```text
VNEGUIDE_LLM_PROVIDER=mock
VNEGUIDE_MODEL=mock-scripted
VNEGUIDE_LITELLM_BASE_URL=https://litellm.example.invalid
VNEGUIDE_LITELLM_API_KEY=
VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=0
VNEGUIDE_LITELLM_DISABLE_THINKING=1
VNEGUIDE_API_KEY=
VNEGUIDE_SESSION_FACTORY=vneguide.core:create_session
VNEGUIDE_CHAT_CORE_VARIANT=guided
VNEGUIDE_RUN_LIVE_SMOKE=0
VNEGUIDE_OCR_ENABLED=0
VNEGUIDE_OCR_MODEL=gpt-5.5
VNEGUIDE_OCR_OPENAI_API_KEY=
VNEGUIDE_OCR_WORKER_TOKEN=
```

Không commit `.env`, API key, dữ liệu cá nhân thật hoặc transcript chứa số định danh đầy đủ. Dữ liệu test trong repo phải là dữ liệu giả.

`VNEGUIDE_LLM_PROVIDER` là tên provider (`mock`, `openai` hoặc `litellm`), không phải URL.
Để dùng LiteLLM, đổi provider thành `litellm`, đặt model ID đã deploy và cung cấp endpoint/key hợp lệ.
`openai` tiếp tục dùng endpoint HTTPS chính thức đã khóa cứng. `litellm` dùng base URL riêng và
tự nối `/v1/chat/completions`. HTTP bị từ chối mặc định; chỉ bật
`VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=1` cho gateway dev tin cậy và dữ liệu tổng hợp. Bearer key,
prompt và phản hồi đều không được mã hóa khi đi qua HTTP; dữ liệu hành chính thật phải dùng HTTPS.

## Quality gates

```powershell
python -m ruff check src tests deployment
python -m ruff format --check src tests deployment
python -m mypy
python -m pytest
python deployment/scripts/release_audit.py
Set-Location demoweb
npm ci
npm audit --audit-level=moderate
npm run check
```

Chạy coverage:

```powershell
python -m pytest --cov=vneguide --cov-report=term-missing
```

Đánh giá A/B deterministic cho câu trả lời nghiệp vụ của đúng ba thủ tục:

```powershell
python -m tests.evals.run_chat_core_ab
```

Lệnh chỉ in metrics tổng hợp, model là `null` vì reply layer không gọi model và không ghi tin nhắn,
draft hoặc dữ liệu cá nhân vào report.

Smoke trực tiếp provider, không phụ thuộc `core` hoặc CLI, bằng đúng một câu tổng hợp không có PII:

```powershell
python -m vneguide.ai.smoke --env-file .env --confirm-live
```

Kết quả thành công có prefix `MODEL_SMOKE_OK`; lệnh không in prompt, raw response, evidence hoặc
API key. `--confirm-live` là bắt buộc để tránh vô tình gửi request mạng.

Live-model integration test là gate chủ động, không chạy mặc định. Hook
`vneguide.core:create_session` đã được triển khai; cấu hình provider, model và key trong environment
rồi chạy:

```powershell
$env:VNEGUIDE_RUN_LIVE_SMOKE="1"
$env:VNEGUIDE_LITELLM_API_KEY="<secret>" # hoặc VNEGUIDE_API_KEY với provider openai
python -m pytest tests/integration/test_live_smoke.py -m live
```

## Container, public smoke và rollback

Stack release giữ đồng thời LiteLLM/OpenAI/mock provider, FastAPI, Next.js và một gateway chung:

```powershell
$env:VNEGUIDE_LLM_PROVIDER="mock"
$env:VNEGUIDE_MODEL="mock-scripted"
docker compose -f deployment/docker-compose.yml up --build --detach --wait
python deployment/scripts/smoke.py `
  --api-url http://127.0.0.1:8080 `
  --web-url http://127.0.0.1:8080 `
  --samples 5 `
  --provider mock `
  --model mock-scripted
```

API demo chạy một worker vì session store nằm trong memory. Hướng dẫn public preview, model secret,
metrics và deploy bền vững nằm trong [`deployment/README.md`](deployment/README.md). Quy trình phục
hồi không force-push nằm trong [`doc/operations/rollback.md`](doc/operations/rollback.md); kịch bản
pitch/video nằm trong [`doc/operations/demo-and-pitch.md`](doc/operations/demo-and-pitch.md).

## Cấu trúc repository

```text
data/
├── catalog/       # Procedure packs, field catalog, rules và source register
├── contracts/     # JSON Schema dùng để validate data package
├── evaluation/    # Bộ dữ liệu đánh giá có ground truth
├── references/    # Tài liệu nguồn được lưu cục bộ
├── qa/            # Checksum kiểm tra tính toàn vẹn
├── docs/          # Quy trình review và quyết định của data package
└── */             # Dataset discovery/RAG seed

doc/               # Requirement, product, architecture và tài liệu vận hành
src/vneguide/      # Source code ứng dụng
tests/             # Unit, integration và evaluation tests
```

## Cấu trúc source code

```text
src/vneguide/
├── domain/     # Contract, enum và model dùng chung — Người 1
├── data/       # Loader/repository truy cập data package — Người 1
├── ai/         # Provider và structured extraction — Người 2
├── core/       # Conversation orchestrator và state — Người 3
├── rules/      # Required fields và validation — Người 3
└── cli/        # Terminal I/O và renderer — Người 4

tests/
├── unit/
├── integration/
└── evals/
```

CLI chỉ gọi public integration port, không chứa business rule và không định nghĩa lại domain model.

## Quy ước dữ liệu

- `data/catalog/` là nguồn dữ liệu runtime đã chuẩn hóa; không tạo bản sao trong `src/`.
- `src/vneguide/data/` chỉ chứa code đọc và kiểm tra data package.
- Tài liệu nguồn chỉ lưu tại `data/references/`.
- Dataset discovery không được dùng trực tiếp để kết luận nghiệp vụ.
- Không commit `.env`, API key, cache, log hoặc dữ liệu cá nhân thật.
