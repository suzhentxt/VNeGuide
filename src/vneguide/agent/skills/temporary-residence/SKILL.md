---
name: temporary-residence
description: Thủ tục đăng ký tạm trú (mã 1.004194). Dùng khi công dân hỏi về đăng ký tạm trú, lệ phí tạm trú, giấy tờ tạm trú, thời hạn tạm trú, hoặc muốn nộp hồ sơ đăng ký tạm trú.
---

# Thủ tục 1.004194 — Đăng ký tạm trú

## Khi nào dùng skill này

Công dân nhắc đến: đăng ký tạm trú, tạm trú, chuyển nơi ở tạm thời, hoặc nêu mã
1.004194.

## Trả lời thông tin (informational)

Khi công dân HỎI (chưa nộp hồ sơ), gọi tool để lấy data đã review:

- Lệ phí → `get_procedure_fee("1.004194")`
- Thời hạn → `get_processing_time("1.004194")`
- Giấy tờ cần nộp → `get_required_documents("1.004194")`
- Thông tin cần cung cấp → `get_required_information("1.004194")`
- Cơ quan thụ lý → `get_authority("1.004194")`
- Kênh nộp → `get_submission_channels("1.004194")`
- Kết quả → `get_result("1.004194")`
- Trình tự thực hiện → `get_guidance_steps("1.004194")`
- Căn cứ pháp lý → `get_legal_basis("1.004194")`
- Điều kiện & phạm vi → `get_conditions_and_limits("1.004194")`
- Hướng dẫn điền 1 field → `get_field_help("1.004194", "<field_id>")`

Tổng hợp kết quả tool thành câu trả lời tự nhiên, KHÔNG copy raw JSON.

## Thu thập hồ sơ (form-filling)

Khi công dân muốn NỘP hồ sơ, thu thập các field theo thứ tự:

1. `registration_mode` — hình thức đăng ký (enum)
2. `applicant_full_name` — họ tên người đăng ký
3. `applicant_date_of_birth` — ngày sinh (date)
4. `applicant_personal_id` — số định danh cá nhân
5. `applicant_is_minor` — người đăng ký chưa thành niên (boolean)
6. `minor_consent_present` — có ý kiến đồng ý của cha/mẹ/giám hộ (boolean)
7. `temporary_address` — địa chỉ tạm trú
8. `temporary_start_date` — ngày bắt đầu tạm trú (date)
9. `temporary_end_date` — ngày kết thúc dự kiến (date)
10. `legal_dwelling_data_retrievable` — thông tin chỗ ở khai thác được từ CSDL (boolean)
11. `legal_dwelling_document_present` — có giấy tờ chứng minh chỗ ở hợp pháp (boolean)
12. `dwelling_basis` — căn cứ sử dụng chỗ ở (enum)
13. `owner_or_householder_consent` — có sự đồng ý của chủ hộ/chủ sở hữu (boolean)
14. `submission_channel` — kênh nộp (enum)
15. `fee_exemption_claimed` — đề nghị miễn lệ phí (boolean)

Dùng `get_missing_fields("1.004194", draft_values)` để biết field nào còn thiếu,
`get_field_question("1.004194", "<field_id>")` để lấy câu hỏi gợi ý.
Hỏi từng field, một lần một câu. Sau khi thu đủ, dùng `validate_draft` để kiểm tra.
