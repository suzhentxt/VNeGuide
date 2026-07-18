---
name: birth-certificate-copy
description: Thủ tục cấp bản sao Giấy khai sinh / Trích lục hộ tịch (mã 2.000635). Dùng khi công dân muốn xin bản sao GKS, hỏi về lệ phí, giấy tờ, thời hạn, hoặc muốn nộp hồ sơ xin bản sao khai sinh.
---

# Thủ tục 2.000635 — Cấp bản sao Trích lục hộ tịch (bản sao GKS)

## Khi nào dùng skill này

Công dân nhắc đến: bản sao giấy khai sinh, trích lục hộ tịch, xin bản sao GKS,
đổi giấy khai sinh, hoặc nêu mã 2.000635.

## Trả lời thông tin (informational)

Khi công dân HỎI (chưa nộp hồ sơ), gọi tool để lấy data đã review:

- Lệ phí → `get_procedure_fee("2.000635")`
- Thời hạn → `get_processing_time("2.000635")`
- Giấy tờ cần nộp → `get_required_documents("2.000635")`
- Thông tin cần cung cấp → `get_required_information("2.000635")`
- Cơ quan thụ lý → `get_authority("2.000635")`
- Kênh nộp → `get_submission_channels("2.000635")`
- Kết quả → `get_result("2.000635")`
- Trình tự thực hiện → `get_guidance_steps("2.000635")`
- Căn cứ pháp lý → `get_legal_basis("2.000635")`
- Điều kiện & phạm vi → `get_conditions_and_limits("2.000635")`
- Hướng dẫn điền 1 field → `get_field_help("2.000635", "<field_id>")`

Tổng hợp kết quả tool thành câu trả lời tự nhiên, KHÔNG copy raw JSON.

## Thu thập hồ sơ (form-filling)

Khi công dân muốn NỘP hồ sơ, thu thập các field theo thứ tự:

1. `requester_type` — loại người yêu cầu (enum)
2. `requester_full_name` — họ tên người yêu cầu
3. `requester_personal_id` — số định danh cá nhân
4. `requester_id_document_type` — loại giấy tờ tùy thân (enum)
5. `requester_residence` — nơi cư trú
6. `subject_full_name` — họ tên người có sự kiện khai sinh
7. `subject_date_of_birth` — ngày sinh (date)
8. `birth_registration_place` — nơi đã đăng ký khai sinh
9. `birth_registration_year` — năm đăng ký khai sinh (integer)
10. `birth_book_number` — số quyển/số đăng ký hộ tịch
11. `copies_requested` — số bản sao yêu cầu (integer)
12. `submission_channel` — kênh nộp (enum)
13. `authorization_relationship` — quan hệ với người ủy quyền (enum, nếu có)

Dùng `get_missing_fields("2.000635", draft_values)` để biết field nào còn thiếu,
`get_field_question("2.000635", "<field_id>")` để lấy câu hỏi gợi ý cho field đó.
Hỏi từng field, một lần một câu. Sau khi thu đủ, dùng `validate_draft` để kiểm tra.
