# Rules

Owner: Người 3.

Rule engine thực thi deterministic handler theo `rule_id` đã review. Chuỗi `condition` trong catalog chỉ là mô tả và không được đưa vào `eval/exec`.

Module cung cấp:

- `RuleEngine.validate`: chạy 27 rule và trả `ValidationResult` có source.
- `RuleEngine.missing_fields`: xác định required/conditional field theo thứ tự catalog.
- `RuleEngine.validate_field_value`: kiểm type, enum, pattern, minimum và ngày.
- `RuleEngine.validate_context_signal`: kiểm signal không phải field theo type và `origin` đã
  review. Origin do caller ghi không tự tạo provenance. `RuleEngine.validate` chỉ cho signal text
  vào handler khi ID nằm trong `confirmed_context_signal_ids`; signal `document_check`/`derived`
  phải nằm trong `trusted_adapter_signal_ids`. Hai tập ID này chỉ được dựng từ state nội bộ đã xác
  nhận hoặc adapter tin cậy, không nhận trực tiếp từ payload client.
- `validate(..., context_signals=..., context_origins=...)` giữ signal tách khỏi form values trước
  khi hợp nhất tạm thời để chạy handler.
- `QuestionSelector`: tạo câu hỏi tiếp theo từ label đã review.

Trạng thái ưu tiên: `out_of_scope` → `needs_correction` → `needs_official_review` → `ready_to_submit`. Issue `info` không chặn hồ sơ.

`validate` hiện đánh giá rule; completeness vẫn được trả riêng bởi `missing_fields`. Một số gold case
đang kỳ vọng `ready_to_submit` dù thiếu field required, nên ý nghĩa trạng thái tổng hợp cần được khóa
ở OD-006 trước khi đổi contract hoặc ground truth.
