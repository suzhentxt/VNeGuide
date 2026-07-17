# HÀNH CHÍNH DỄ — AI giúp chuẩn bị hồ sơ đúng ngay từ đầu

## Vấn đề

Khi làm khai sinh, đăng ký thường trú hoặc xin giấy phép xây dựng, người dân thường không biết cần giấy tờ gì, điền đúng chưa và phải nộp ở đâu. Sai sót chỉ được phát hiện tại bước tiếp nhận, dẫn đến bổ sung hồ sơ, đi lại nhiều lần và tăng tải cho cán bộ hỗ trợ.

## Giải pháp

**Hành Chính Dễ** là trợ lý AI nhúng trực tiếp vào cổng dịch vụ công:

1. **Guided intake:** hiểu nhu cầu bằng tiếng Việt, hỏi làm rõ và tạo checklist cùng quy trình từng bước.
2. **Pre-submission check:** đọc form/ảnh/PDF, cho người dùng xác nhận dữ liệu, phát hiện trường thiếu, sai định dạng và thông tin không khớp.
3. **Seamless integration:** cung cấp widget iframe và REST API, không yêu cầu cài ứng dụng mới.

Mọi yêu cầu hồ sơ đến từ rule pack đã duyệt và có nguồn; LLM chỉ giúp hiểu ngôn ngữ, trích xuất và giải thích. Kết quả không thay thế quyết định của cơ quan nhà nước.

## Người dùng và phạm vi pilot

- Công dân Hà Nội, đặc biệt người ít kinh nghiệm với dịch vụ công trực tuyến.
- Người thân hỗ trợ chuẩn bị hồ sơ.
- Cán bộ một cửa muốn giảm câu hỏi và lỗi lặp lại.

MVP hỗ trợ đăng ký khai sinh, đăng ký thường trú và cấp giấy phép xây dựng mới cho nhà ở riêng lẻ.

## Giá trị đo lường

- 100% giấy tờ bắt buộc trong gold set được nhắc đúng.
- Missing-field recall mục tiêu ≥95%, issue precision ≥90%.
- Ít nhất 5/6 người test hoàn thành không cần trợ giúp; SUS ≥80.
- Pilot hướng tới tăng 20 điểm phần trăm tỷ lệ đúng ngay lần đầu và giảm 25% câu hỏi hỗ trợ.

## Kiến trúc và an toàn

Portal → iframe widget → REST API → rule engine + versioned official sources + Gemini multimodal. File chỉ được xử lý trong bộ nhớ, không lưu; người dùng demo được yêu cầu dùng dữ liệu mẫu. Mọi hướng dẫn hiển thị nguồn, ngày kiểm chứng và phạm vi áp dụng Hà Nội.

## Roadmap

- **5 ngày hackathon:** ba procedure packs, widget, guided intake, document check, public demo, eval và tài liệu.
- **4–8 tuần pilot:** 100–300 người dùng, reviewer nghiệp vụ, đo first-time-right, support time và false positives.
- **2–3 tháng:** dashboard duyệt nguồn, tự phát hiện thay đổi và mở rộng theo lĩnh vực.
- **3–6 tháng:** đánh giá bảo mật/pháp lý, SLA và tích hợp portal/định danh khi có thẩm quyền.

## Tầm nhìn

Biến mỗi thủ tục hành chính thành một hướng dẫn có thể hiểu, có thể kiểm tra và có thể nhúng vào bất kỳ cổng dịch vụ công nào.

