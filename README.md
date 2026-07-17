# VNeGuide Terminal MVP

VNeGuide là chatbot hỗ trợ người dân chuẩn bị và kiểm tra trước hồ sơ dịch vụ công. Phạm vi runtime hiện hành được khóa bởi [`data/README.md`](data/README.md) và gồm:

- `2.000635`: Cấp bản sao Trích lục hộ tịch — bản sao Giấy khai sinh.
- `1.013314`: Xác nhận điều kiện diện tích bình quân nhà ở và tình trạng chỗ ở.
- `1.004194`: Đăng ký tạm trú.

Các tài liệu sản phẩm cũ trong `doc/` phải được đối chiếu với data package trước khi dùng để code. VNeGuide chỉ hỗ trợ hướng dẫn, kiểm tra và chuẩn bị hồ sơ; kết quả không phải quyết định hành chính.

## Yêu cầu

- Python 3.11 trở lên.
- Không cần API key khi dùng mock provider và chạy test mặc định.
- API key chỉ cần cho smoke test provider thật, được bật chủ động.

## Cài đặt

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
```

`.env` đã được Git bỏ qua. Runtime không đọc secret lúc import. Lệnh smoke provider bên dưới chỉ
đọc file được chỉ định rõ bằng `--env-file`; các luồng khác vẫn nhận cấu hình từ environment.

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

Nếu hook `vneguide.core:create_session` chưa được triển khai, CLI dừng với thông báo cấu hình an toàn thay vì traceback. CLI không chứa business logic tạm để thay thế core.

## Cấu hình provider

Các biến mẫu nằm trong `.env.example`:

```text
VNEGUIDE_LLM_PROVIDER=litellm
VNEGUIDE_MODEL=Qwen/Qwen3.5-9B
VNEGUIDE_LITELLM_BASE_URL=http://127.0.0.1:9207
VNEGUIDE_LITELLM_API_KEY=
VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=0
VNEGUIDE_LITELLM_DISABLE_THINKING=1
VNEGUIDE_API_KEY=
VNEGUIDE_SESSION_FACTORY=vneguide.core:create_session
VNEGUIDE_RUN_LIVE_SMOKE=0
```

Không commit `.env`, API key, dữ liệu cá nhân thật hoặc transcript chứa số định danh đầy đủ. Dữ liệu test trong repo phải là dữ liệu giả.

`VNEGUIDE_LLM_PROVIDER` là tên provider (`mock`, `openai` hoặc `litellm`), không phải URL.
`openai` tiếp tục dùng endpoint HTTPS chính thức đã khóa cứng. `litellm` dùng base URL riêng và
tự nối `/v1/chat/completions`. HTTP bị từ chối mặc định; chỉ bật
`VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=1` cho gateway dev tin cậy và dữ liệu tổng hợp. Bearer key,
prompt và phản hồi đều không được mã hóa khi đi qua HTTP; dữ liệu hành chính thật phải dùng HTTPS.

## Quality gates

```powershell
python -m ruff check .
python -m ruff format --check src/vneguide/cli tests/integration tests/evals
python -m mypy
python -m pytest
```

Chạy coverage:

```powershell
python -m pytest --cov=vneguide --cov-report=term-missing
```

Smoke trực tiếp provider, không phụ thuộc `core` hoặc CLI, bằng đúng một câu tổng hợp không có PII:

```powershell
python -m vneguide.ai.smoke --env-file .env --confirm-live
```

Kết quả thành công có prefix `MODEL_SMOKE_OK`; lệnh không in prompt, raw response, evidence hoặc
API key. `--confirm-live` là bắt buộc để tránh vô tình gửi request mạng.

Live session test cũ vẫn là gate end-to-end và chỉ dùng được sau khi
`vneguide.core:create_session` được triển khai. Khi đó cấu hình provider, model và key trong
environment rồi chạy:

```powershell
$env:VNEGUIDE_RUN_LIVE_SMOKE="1"
$env:VNEGUIDE_LITELLM_API_KEY="<secret>" # hoặc VNEGUIDE_API_KEY với provider openai
python -m pytest tests/integration/test_live_smoke.py -m live
```

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
