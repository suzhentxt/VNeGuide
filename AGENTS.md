# AGENTS.md

Các chỉ dẫn này áp dụng cho toàn bộ repository VNeGuide. Mục tiêu là để mỗi phiên coding-agent tạo ra thay đổi nhỏ, có bằng chứng và có thể bàn giao mà không cần đoán lại trạng thái project.

## Khởi động phiên

Trước khi sửa code:

1. Xác nhận đang làm việc tại repository `VAIC_UET`.
2. Chạy `git status --short` và `git log --oneline -5`.
3. Đọc `README.md`, `data/README.md` và `doc/README.md`.
4. Đọc `doc/operations/progress.md` và `doc/operations/session-handoff.md`.
5. Chọn đúng một đầu việc chưa hoàn thành có ưu tiên cao nhất.
6. Chạy baseline phù hợp đang có trong repo trước khi thêm tính năng.

Repo hiện chưa có `feature_list.json`, `init.sh` hoặc CLI chạy được. Không giả định các artifact này tồn tại. Khi thêm bootstrap, ưu tiên PowerShell trên Windows và cập nhật tài liệu vận hành trong cùng PR.

## Nguồn sự thật

Ưu tiên theo thứ tự:

1. `data/README.md` khóa phạm vi thủ tục hiện hành.
2. `data/catalog/` chứa procedure pack, field catalog, rule và source register.
3. `data/contracts/` chứa JSON Schema của data package.
4. `data/evaluation/` chứa ground truth đánh giá.
5. `doc/` chứa requirement và tài liệu thiết kế; tài liệu cũ không được ghi đè data package đã review.

Nếu các nguồn mâu thuẫn, không tự chọn theo suy đoán. Ghi quyết định cần xử lý vào `data/docs/open_decisions.json`.

## Ranh giới module

- `src/vneguide/domain/`: contract, enum và model dùng chung.
- `src/vneguide/data/`: code đọc data package; không sao chép JSON runtime vào source.
- `src/vneguide/ai/`: provider adapter, prompt và structured extraction.
- `src/vneguide/core/`: orchestration và state transition; không phụ thuộc CLI.
- `src/vneguide/rules/`: business rule và validation xác định.
- `src/vneguide/cli/`: input/output terminal; không chứa business logic.

Không tự tạo một bộ enum hoặc field name riêng trong từng module.

## Quy tắc làm việc

- Mỗi phiên tập trung vào một đầu việc hoặc một lỗi cụ thể.
- LLM được phép chủ động gọi tool truy xuất phí, thời hạn, giấy tờ, căn cứ pháp lý
  từ data package đã review. LLM KHÔNG được tự bịa; mọi câu trả lời dựa trên data
  tool trả về và truy được về `source_id` đã review.
- Tool chỉ trả data đã review trong `data/catalog/`; tool không cho LLM ghi đè,
  sáng tác hoặc suy luận sự kiện nghiệp vụ.
- LLM không được thay cơ quan có thẩm quyền kết luận đủ điều kiện hồ sơ; chỉ
  `RuleEngine` và `ProcedureQAResponder` là nguồn sự thật nghiệp vụ.
- Không thay schema, ground truth hoặc quality gate chỉ để làm test pass.
- Không commit secret, `.env`, log chứa PII hoặc dữ liệu cá nhân thật.
- Không sửa dataset discovery để che lỗi của application.
- Giữ thay đổi trong đúng module owner được mô tả trong kế hoạch terminal.

## Definition of Done

Một đầu việc chỉ hoàn thành khi:

- hành vi mục tiêu đã được triển khai;
- kiểm tra liên quan đã thực sự chạy;
- kết quả và giới hạn xác minh được ghi vào `doc/operations/progress.md`;
- không còn conflict marker hoặc thay đổi ngoài scope;
- người tiếp theo có lệnh hoặc bước cụ thể để tiếp tục.

## Kết thúc phiên

1. Chạy lại kiểm tra liên quan.
2. Cập nhật `doc/operations/progress.md`.
3. Cập nhật `doc/operations/session-handoff.md` nếu còn việc dở hoặc blocker.
4. Kiểm tra `doc/operations/clean-state-checklist.md`.
5. Commit khi working state an toàn; không tự push nếu người dùng chưa yêu cầu.
