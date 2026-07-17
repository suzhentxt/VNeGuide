# VNeGuide Terminal MVP

VNeGuide là chatbot tiếng Việt hỗ trợ người dân chuẩn bị hồ sơ **cấp bản sao trích lục hộ tịch** cho ba loại sự kiện: khai sinh, kết hôn và khai tử. MVP hiện tại chạy trong terminal; đăng ký sự kiện hộ tịch mới, nộp hồ sơ thật, VNeID, OTP và thanh toán đều nằm ngoài phạm vi.

VNeGuide chỉ hỗ trợ hướng dẫn, kiểm tra và chuẩn bị hồ sơ. Kết quả không phải quyết định hành chính và không thay thế việc kiểm tra của cơ quan có thẩm quyền.

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

`.env` đã được Git bỏ qua. Project không tự động đọc file này; hãy export các biến cần dùng trong shell hoặc dùng công cụ nạp `.env` của môi trường phát triển.

## Chạy chatbot

Lệnh thống nhất:

```powershell
python -m vneguide.cli
```

CLI nạp session factory từ `VNEGUIDE_SESSION_FACTORY`, mặc định là `vneguide.core:create_session`. Factory này do lớp tích hợp core cung cấp và phải trả về một session có phương thức `send(message) -> TurnResult`. Thiết kế này giữ CLI độc lập với implementation của LLM, rule engine và state machine.

Các lệnh trong phiên:

- `/status`: in lại trạng thái hồ sơ gần nhất.
- `/reset`: hủy state hiện tại và tạo session mới.
- `/quit`: đóng session và thoát.

Mỗi lượt hiển thị câu trả lời, thủ tục nhận diện, dữ liệu trích xuất, hồ sơ nháp, trường còn thiếu, lỗi validation, nguồn tham khảo và bước tiếp theo. Giá trị của các field định danh phổ biến như `cccd` được che trước khi hiển thị.

Ở trạng thái repo nền, nếu hook `vneguide.core:create_session` chưa được merge, CLI sẽ dừng với thông báo cấu hình rõ ràng thay vì traceback. Không thêm business logic tạm vào CLI để thay thế core.

## Cấu hình provider

Các biến mẫu nằm trong `.env.example`:

```text
VNEGUIDE_LLM_PROVIDER=mock
VNEGUIDE_MODEL=
VNEGUIDE_API_KEY=
VNEGUIDE_SESSION_FACTORY=vneguide.core:create_session
VNEGUIDE_RUN_LIVE_SMOKE=0
```

Không commit `.env`, API key, dữ liệu cá nhân thật hoặc transcript chứa số định danh đầy đủ. Dữ liệu test trong repo phải là dữ liệu giả.

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

Smoke test provider thật mặc định bị skip. Chỉ chạy khi đã cấu hình provider, model và key trong môi trường:

```powershell
$env:VNEGUIDE_RUN_LIVE_SMOKE="1"
$env:VNEGUIDE_API_KEY="<secret>"
python -m pytest tests/integration/test_live_smoke.py -m live
```

## Kiến trúc source

```text
src/vneguide/
├── domain/     # Contract, enum và model dùng chung — Người 1
├── data/       # Dữ liệu thủ tục và nguồn — Người 1
├── ai/         # Provider và structured extraction — Người 2
├── core/       # Conversation orchestrator và state — Người 3
├── rules/      # Required fields và validation — Người 3
└── cli/        # Terminal I/O và renderer — Người 4

tests/
├── unit/
├── integration/
└── evals/
```

CLI chỉ gọi public integration port, không chứa business rule và không định nghĩa lại domain model. Xem [phân công Terminal MVP](doc/Terminal%20MVP%20-%20Chia%20task%204%20nguoi.md) để biết contract và kịch bản nghiệm thu.
