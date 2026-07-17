# VNeGuide Terminal MVP — Chia task cho 4 người

> **Trạng thái:** Kế hoạch kỹ thuật ban đầu. Phạm vi ba loại trích lục trong tài liệu này đã cũ so với Domain & Data Package v2. Khi code, dùng danh sách thủ tục và enum được phê duyệt trong [`../data/README.md`](../data/README.md), đồng thời giữ nguyên ranh giới module và quy trình merge mô tả bên dưới.

## 1. Mục tiêu giai đoạn hiện tại

Xây dựng chatbot VNeGuide chạy được trong terminal và trả lời đúng nghiệp vụ tối thiểu trước khi tích hợp vào web.

Phạm vi hỗ trợ gồm ba thủ tục:

- Cấp bản sao trích lục khai sinh (`birth_extract`).
- Cấp bản sao trích lục kết hôn (`marriage_extract`).
- Cấp bản sao trích lục khai tử (`death_extract`).
- Nhận diện và từ chối an toàn các yêu cầu ngoài phạm vi (`unsupported`).

Chatbot phải:

- Hiểu nhu cầu được nhập bằng tiếng Việt tự nhiên.
- Hỏi bổ sung thông tin còn thiếu mà không hỏi lặp lại dữ liệu đã có.
- Chuyển thông tin hội thoại thành dữ liệu có cấu trúc.
- Kiểm tra trường bắt buộc, định dạng và một số mâu thuẫn nghiệp vụ.
- Không tự đoán thông tin còn thiếu.
- Không tự kết luận hồ sơ đã được cơ quan nhà nước chấp nhận.
- Trả hướng dẫn dựa trên dữ liệu thủ tục đã được khai báo và có nguồn.

## 2. Ngoài phạm vi

Giai đoạn này chưa thực hiện:

- Giao diện web hoặc widget.
- API HTTP phục vụ frontend.
- Database hoặc vector database production.
- Đăng nhập, VNeID, OTP hoặc chữ ký số.
- Thanh toán hoặc nộp hồ sơ thật.
- Deploy lên URL công khai.
- Đăng ký khai sinh, kết hôn hoặc khai tử mới.
- Đăng ký lại sự kiện hộ tịch.

## 3. Kiến trúc terminal tối thiểu

```text
Người dùng nhập trong terminal
        ↓
Conversation Orchestrator
        ├── LLM Extractor
        │     ├── Phân loại nhu cầu
        │     └── Trích xuất dữ liệu có cấu trúc
        ├── Procedure Catalog
        │     └── Checklist, hướng dẫn và nguồn
        ├── Rule Engine
        │     └── Trường bắt buộc và câu hỏi tiếp theo
        └── Validator
              └── Định dạng, dữ liệu thiếu và mâu thuẫn
        ↓
Câu trả lời + trạng thái hồ sơ dạng JSON
```

LLM chỉ đảm nhiệm hiểu ngôn ngữ và trích xuất dữ liệu. Rule Engine và dữ liệu thủ tục quyết định trường bắt buộc, tính hợp lệ, checklist và hướng dẫn nghiệp vụ.

## 4. Cấu trúc thư mục thống nhất

```text
src/vneguide/
├── domain/          # Schema, enum và model dùng chung
├── data/            # Dữ liệu ba thủ tục và nguồn tham khảo
├── ai/              # Provider, prompt và structured extraction
├── core/            # State machine và conversation orchestrator
├── rules/           # Required fields và validation
└── cli/             # Vòng lặp chatbot terminal

tests/
├── unit/
├── integration/
└── evals/
```

Không tự tạo thêm một bộ model, enum hoặc field name riêng trong từng module.

## 5. Contract dùng chung

Contract tối thiểu cho một lượt hội thoại:

```python
TurnRequest(
    message: str,
    state: ConversationState,
)

TurnResult(
    reply: str,
    procedure_type: ProcedureType,
    extracted_fields: dict,
    draft: CaseDraft,
    missing_fields: list[str],
    validation_issues: list[ValidationIssue],
    source_ids: list[str],
    next_action: str,
)
```

Enum thủ tục duy nhất:

```text
birth_extract
marriage_extract
death_extract
unsupported
```

`CaseDraft` tối thiểu chứa:

- Thông tin người yêu cầu.
- Thông tin người được trích lục.
- Loại sự kiện hộ tịch.
- Quan hệ giữa người yêu cầu và người được trích lục.
- Nơi đăng ký hộ tịch.
- Thời gian hoặc năm đăng ký.
- Hình thức nhận kết quả.
- Các trường đã được người dùng xác nhận.

## 6. Phân công

### Người 1 — Domain contract và dữ liệu nghiệp vụ

Phạm vi sở hữu:

```text
src/vneguide/domain/**
src/vneguide/data/**
tests/unit/test_procedure_data.py
```

Nhiệm vụ:

- Định nghĩa `ProcedureType`, `CaseDraft`, `Applicant`, `Subject`, `ConversationState` và `ValidationIssue`.
- Chốt tên field dùng xuyên suốt project.
- Tạo dữ liệu có cấu trúc cho ba thủ tục.
- Khai báo checklist, trường bắt buộc, hướng dẫn, cơ quan thực hiện và nguồn tham khảo.
- Thêm ngày kiểm tra và phiên bản dữ liệu.
- Viết test bảo đảm toàn bộ procedure fixture vượt schema validation.

Không thực hiện:

- Không viết prompt.
- Không viết CLI.
- Không để LLM tự sinh checklist hoặc quy định.

Đầu ra hoàn thành:

- Các schema import được từ module khác.
- Ba procedure fixture hợp lệ.
- Field name và enum được khóa để Người 2–4 sử dụng.

### Người 2 — LLM và structured extraction

Phạm vi sở hữu:

```text
src/vneguide/ai/**
tests/unit/test_extractor.py
tests/evals/intent_cases.*
```

Nhiệm vụ:

- Định nghĩa interface `LLMProvider`.
- Phân loại đúng bốn intent đã thống nhất.
- Trích xuất slot từ câu người dùng sang schema của Người 1.
- Bắt buộc dùng structured output.
- Khi output sai schema: retry có giới hạn rồi trả fallback an toàn.
- Không tự đoán giá trị thiếu hoặc kết luận hồ sơ hợp lệ.
- Cấu hình model và API key qua biến môi trường.
- Tạo mock provider để test không gọi model thật.

Không thực hiện:

- Không tự định nghĩa schema song song.
- Không quyết định required fields.
- Không viết validation nghiệp vụ.
- Không gọi SDK model trực tiếp từ CLI hoặc orchestrator.

Đầu ra hoàn thành:

- Input tiếng Việt được chuyển thành JSON đúng schema.
- Có test intent, slot extraction, malformed output và timeout.
- Test chạy được khi không có API key.

### Người 3 — Conversation engine, rules và validation

Phạm vi sở hữu:

```text
src/vneguide/core/**
src/vneguide/rules/**
tests/unit/test_rules.py
tests/unit/test_conversation.py
```

Nhiệm vụ:

- Xây dựng state machine cho hội thoại nhiều lượt.
- Merge slot mới vào draft hiện tại.
- Không ghi đè dữ liệu người dùng đã xác nhận.
- Xác định field thiếu và câu hỏi tiếp theo bằng rule cố định.
- Không hỏi lại field đã có và hợp lệ.
- Kiểm tra field bắt buộc.
- Kiểm tra CCCD gồm 12 chữ số.
- Kiểm tra ngày tháng hợp lệ và không nằm vô lý trong tương lai.
- Kiểm tra nơi và thời gian đăng ký hộ tịch.
- Kiểm tra quan hệ giữa người yêu cầu và người được trích lục.
- Giới hạn số lần hỏi lại để tránh vòng lặp.
- Tạo `TurnResult` độc lập với terminal và web.

Không thực hiện:

- Không đưa business rule vào prompt.
- Không đọc input hoặc in output trực tiếp trong core engine.
- Không phụ thuộc model thật trong unit test.

Đầu ra hoàn thành:

- Engine chạy hoàn toàn với mock extractor.
- Hội thoại nhiều lượt giữ đúng state.
- Validation issue chỉ rõ field, lý do và cách sửa.

### Người 4 — CLI, integration và quality gate

Phạm vi sở hữu:

```text
src/vneguide/cli/**
tests/integration/**
tests/evals/**
pyproject.toml
.env.example
README.md
```

Người 4 đồng thời là integration owner.

Nhiệm vụ:

- Tạo lệnh chạy thống nhất:

```powershell
python -m vneguide.cli
```

- Hiển thị câu trả lời, thủ tục đã nhận diện, dữ liệu đã thu thập, field còn thiếu, lỗi validation và nguồn tham khảo.
- Hỗ trợ các lệnh `/status`, `/reset` và `/quit`.
- Viết integration test cho các luồng demo.
- Thiết lập formatter, type check và test runner.
- Viết hướng dẫn cài đặt và chạy project.
- Chạy toàn bộ test sau mỗi lần merge.
- Kiểm tra không có API key hoặc dữ liệu cá nhân giả lập bị commit.

Không thực hiện:

- Không sửa logic thuộc module của Người 1–3 để chữa test tạm thời.
- Không thay field name hoặc wire contract mà chưa có xác nhận của Người 1.
- Chưa xây API HTTP hoặc giao diện web.

Đầu ra hoàn thành:

- Clone mới, cài dependency và chạy chatbot được theo README.
- Integration tests chạy được với mock provider.
- Có một smoke test tùy chọn với provider thật.

## 7. Quy trình Git và merge

### Bước 1 — Commit nền

Người 4 tạo một commit nền duy nhất gồm:

- Package structure.
- `pyproject.toml`.
- Formatter, type checker và test runner.
- File `.env.example` không chứa secret.

Sau commit này, cả nhóm tạo branch riêng.

### Bước 2 — Khóa contract

Người 1 hoàn thành domain schema, enum và procedure fixtures trước. PR của Người 1 phải được merge đầu tiên.

Sau đó Người 2–4 rebase branch lên contract vừa merge.

### Bước 3 — Làm song song theo ranh giới file

- Người 2 chỉ dùng schema của Người 1 để tạo extractor.
- Người 3 dùng schema và mock extractor để hoàn thiện engine.
- Người 4 dùng mock `TurnResult` để dựng CLI và integration harness.

### Bước 4 — Thứ tự merge

1. Người 1: domain schema và procedure data.
2. Người 2: AI provider và extractor.
3. Người 3: conversation engine, rules và validation.
4. Người 4: CLI, integration tests và tài liệu chạy.

### Quy tắc tránh conflict

- Không cho hai người cùng sửa `domain/models.py`.
- Chỉ Người 4 sửa `pyproject.toml` và README trong giai đoạn này.
- Mọi thay đổi field name phải đi qua PR của Người 1.
- Không copy model dùng chung vào module riêng.
- Mỗi PR phải nhỏ, có test và chỉ chạm đúng phạm vi sở hữu.
- Trước khi merge phải rebase lên nhánh chính và chạy toàn bộ test.
- Không merge nếu structured output, schema và engine dùng enum khác nhau.

## 8. Kịch bản nghiệm thu bắt buộc

### Kịch bản 1 — Trích lục khai sinh

Input:

```text
Tôi cần xin lại giấy khai sinh.
```

Kết quả mong đợi:

- Nhận diện `birth_extract`.
- Làm rõ đây là cấp bản sao trích lục, không phải đăng ký khai sinh mới hoặc đăng ký lại.
- Hỏi các thông tin còn thiếu.

### Kịch bản 2 — Trích lục khai tử cho người thân

Kết quả mong đợi:

- Nhận diện `death_extract`.
- Hỏi người được trích lục là ai.
- Hỏi quan hệ với người yêu cầu.
- Hỏi nơi và thời gian đăng ký khai tử.
- Không tự suy đoán giấy tờ chứng minh.

### Kịch bản 3 — Yêu cầu kết hôn chưa rõ

Input:

```text
Tôi cần giấy xác nhận đã kết hôn.
```

Kết quả mong đợi:

- Chưa tự động kết luận `marriage_extract`.
- Hỏi người dùng cần bản sao trích lục kết hôn hay xác nhận tình trạng hôn nhân.
- Nếu là xác nhận tình trạng hôn nhân thì chuyển sang `unsupported` và hướng dẫn an toàn.

### Kịch bản 4 — Ngoài phạm vi

Input:

```text
Tôi muốn đăng ký khai sinh cho con.
```

Kết quả mong đợi:

- Trả `unsupported`.
- Giải thích MVP chỉ hỗ trợ cấp bản sao trích lục.
- Không tạo hoặc điền draft trích lục.

## 9. Definition of Done

Giai đoạn terminal chỉ được coi là hoàn thành khi:

- Cả bốn kịch bản nghiệm thu chạy đúng.
- Ba intent trong phạm vi và intent `unsupported` dùng chung một enum.
- Mọi output từ LLM đều được schema validation trước khi sử dụng.
- Chatbot không bịa thông tin còn thiếu.
- Chatbot không hỏi lặp vô hạn.
- Chatbot không tự tuyên bố hồ sơ được chấp nhận.
- Validation issue nêu rõ field, lý do và cách sửa.
- Procedure guidance có `source_id` hoặc nguồn tham khảo.
- Unit và integration tests chạy được không cần API key.
- Có lệnh terminal duy nhất và README hướng dẫn chạy.
- Core engine không phụ thuộc CLI, để sau này có thể bọc bằng API và tích hợp web mà không viết lại logic.

## 10. Điểm tài liệu cần thống nhất

`Architecture & Delivery.md` đang dùng ví dụ “Tôi muốn đăng ký khai sinh cho con” trong luồng cốt lõi, trong khi `Product and UX.md` xác định đăng ký khai sinh mới nằm ngoài phạm vi MVP.

Trong implementation, áp dụng quy định của tài liệu Product:

- Đăng ký khai sinh mới là `unsupported`.
- VNeGuide chỉ hỗ trợ cấp bản sao trích lục khai sinh trong giai đoạn này.
