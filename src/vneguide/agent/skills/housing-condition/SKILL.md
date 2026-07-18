---
name: housing-condition
description: Thủ tục xác nhận điều kiện diện tích bình quân nhà ở để đăng ký thường trú (mã 1.013314). Dùng khi công dân hỏi về điều kiện nhà ở, diện tích bình quân, hoặc muốn nộp hồ sơ xác nhận điều kiện nhà ở.
---

# Thủ tục 1.013314 — Xác nhận điều kiện diện tích bình quân nhà ở

## Khi nào dùng skill này

Công dân nhắc đến: điều kiện nhà ở, diện tích bình quân, xác nhận nhà ở, đăng
ký thường trú vào chỗ thuê/mượn/ở nhờ, hoặc nêu mã 1.013314.

## Trả lời thông tin (informational)

Khi công dân HỎI (chưa nộp hồ sơ), gọi tool để lấy data đã review:

- Lệ phí → `get_procedure_fee("1.013314")`
- Thời hạn → `get_processing_time("1.013314")`
- Giấy tờ cần nộp → `get_required_documents("1.013314")`
- Thông tin cần cung cấp → `get_required_information("1.013314")`
- Cơ quan thụ lý → `get_authority("1.013314")`
- Kênh nộp → `get_submission_channels("1.013314")`
- Kết quả → `get_result("1.013314")`
- Trình tự thực hiện → `get_guidance_steps("1.013314")`
- Căn cứ pháp lý → `get_legal_basis("1.013314")`
- Điều kiện & phạm vi → `get_conditions_and_limits("1.013314")`
- Hướng dẫn điền 1 field → `get_field_help("1.013314", "<field_id>")`

Tổng hợp kết quả tool thành câu trả lời tự nhiên, KHÔNG copy raw JSON.

## Thu thập hồ sơ (form-filling)

Khi công dân muốn NỘP hồ sơ, thu thập các field theo thứ tự:

1. `requester_full_name` — họ tên người đề nghị
2. `requester_date_of_birth` — ngày sinh (date)
3. `requester_personal_id` — số định danh cá nhân
4. `requester_residence` — nơi cư trú
5. `legal_dwelling_address` — địa chỉ chỗ ở hợp pháp
6. `land_area_m2` — diện tích thửa đất (number)
7. `construction_area_m2` — diện tích xây dựng (number)
8. `floor_area_m2` — diện tích sàn (number)
9. `current_permanent_residents` — tổng số người đang đăng ký thường trú (integer)
10. `remaining_floor_area_m2` — diện tích sàn còn lại (number)
11. `new_residents_count` — số người đề nghị đăng ký (integer)
12. `allocated_area_m2` — tổng diện tích cho người thuê/mượn/ở nhờ (number)
13. `hanoi_zone` — khu vực Hà Nội (enum)
14. `declared_stable_use` — khai chỗ ở sử dụng ổn định (boolean)
15. `declared_no_dispute` — khai nhà/đất không tranh chấp (boolean)
16. `declared_not_prohibited_location` — khai không thuộc địa điểm cấm (boolean)

Dùng `get_missing_fields("1.013314", draft_values)` để biết field nào còn thiếu,
`get_field_question("1.013314", "<field_id>")` để lấy câu hỏi gợi ý.
Hỏi từng field, một lần một câu. Sau khi thu đủ, dùng `validate_draft` để kiểm tra.
