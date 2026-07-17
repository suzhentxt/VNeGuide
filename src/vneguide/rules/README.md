# Rules

Owner: Người 3.

Rule engine thực thi deterministic handler theo `rule_id` đã review. Chuỗi `condition` trong catalog chỉ là mô tả và không được đưa vào `eval/exec`.

Module cung cấp:

- `RuleEngine.validate`: chạy 27 rule và trả `ValidationResult` có source.
- `RuleEngine.missing_fields`: xác định required/conditional field theo thứ tự catalog.
- `RuleEngine.validate_field_value`: kiểm type, enum, pattern, minimum và ngày.
- `QuestionSelector`: tạo câu hỏi tiếp theo từ label đã review.

Trạng thái ưu tiên: `out_of_scope` → `needs_correction` → `needs_official_review` → `ready_to_submit`. Issue `info` không chặn hồ sơ.
