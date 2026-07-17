# User Stories — Bốn paths chính

## Path 1 — Khai sinh từ nhu cầu mơ hồ

**User story:** Là cha/mẹ của trẻ mới sinh, tôi muốn mô tả nhu cầu bằng lời thường để biết mình cần làm thủ tục gì và chuẩn bị gì.

**Điểm bắt đầu:** “Tôi muốn làm giấy tờ cho con mới sinh.”

**Luồng:**

1. Hệ thống đề xuất đăng ký khai sinh và yêu cầu người dùng xác nhận.
2. Hỏi nơi cư trú, tình trạng giấy chứng sinh, quan hệ người làm thủ tục và hình thức nộp.
3. Tạo checklist bắt buộc/có điều kiện.
4. Hiển thị từng bước, ví dụ điền thông tin của trẻ, nơi nộp và citation.
5. Người dùng chuyển sang kiểm tra form.

**Acceptance criteria:**

- Không tự giả định người dùng có giấy chứng sinh.
- Có nhánh giấy tờ thay thế theo nguồn chính thức.
- Phân biệt giấy tờ phải nộp với giấy tờ chỉ cần xuất trình.
- Mọi checklist item có source ID và ngày kiểm chứng.

## Path 2 — Đăng ký thường trú, hồ sơ không có lỗi

**User story:** Là người chuyển về sống cùng gia đình, tôi muốn biết hồ sơ đã đủ chưa trước khi nộp trực tuyến.

**Điểm bắt đầu:** “Tôi chuyển về ở cùng nhà chồng tại Hà Nội và muốn đăng ký thường trú.”

**Luồng:**

1. Xác nhận thủ tục, chỗ ở hợp pháp, quan hệ với chủ hộ/chủ sở hữu và kênh nộp.
2. Hiển thị checklist tương ứng.
3. Người dùng điền form, tải tài liệu mẫu và xác nhận dữ liệu trích xuất.
4. Rule engine kiểm tra trường bắt buộc và điều kiện.
5. Hệ thống trả `pass` cùng phạm vi của kết quả và link nộp chính thức.

**Acceptance criteria:**

- Hiển thị đúng mức phí/kênh nộp theo source version.
- Không yêu cầu lại tài liệu nếu nguồn quy định dữ liệu có thể được khai thác từ cơ sở dữ liệu nhà nước, trừ nhánh fallback.
- Dùng câu “Không phát hiện lỗi trong phạm vi kiểm tra”, không dùng “Hồ sơ hợp lệ”.

## Path 3 — Giấy phép xây dựng có thiếu và xung đột

**User story:** Là chủ nhà chuẩn bị xây mới, tôi muốn hệ thống chỉ rõ chỗ thiếu hoặc thông tin không khớp để sửa trước khi nộp.

**Dữ liệu test:**

- Đơn đề nghị bỏ trống diện tích xây dựng.
- Tên chủ đầu tư trong đơn khác giấy tờ đất do thiếu tên đệm.
- Thiếu một thành phần bản vẽ được checklist yêu cầu.

**Luồng:**

1. Hệ thống xác nhận đây là xây mới nhà ở riêng lẻ, không phải sửa chữa hoặc điều chỉnh giấy phép.
2. Trích xuất tài liệu và yêu cầu người dùng xác nhận.
3. Báo lỗi thiếu diện tích và thiếu bản vẽ bằng deterministic rules.
4. Đánh dấu chênh lệch tên là `needs_review` nếu semantic confidence không đủ cao.
5. Sau khi người dùng sửa, hệ thống cho phép re-check và cập nhật report.

**Acceptance criteria:**

- Lỗi phải chỉ rõ tài liệu, trường, bằng chứng và cách sửa.
- Không tự kết luận hai tên là hai người khác nhau nếu chỉ khác dấu/viết tắt/tên đệm.
- Không đánh giá nội dung kỹ thuật bản vẽ ngoài phạm vi MVP.

## Path 4 — Ngoài phạm vi hoặc không đủ tin cậy

**User story:** Là người có yêu cầu phức tạp, tôi muốn biết khi nào AI không thể trả lời để không chuẩn bị sai hồ sơ.

**Các tình huống:**

- Thủ tục thuộc tỉnh khác.
- Yêu cầu ngoài ba thủ tục.
- Trường hợp có tranh chấp hoặc ngoại lệ pháp lý.
- Ảnh quá mờ/thiếu trang.
- Tài liệu chứa câu lệnh yêu cầu AI bỏ qua quy định.

**Acceptance criteria:**

- Không tạo checklist đoán mò.
- Giải thích rõ giới hạn, thông tin còn thiếu và bước tiếp theo.
- Dẫn tới trang thủ tục/cơ quan chính thức phù hợp nếu xác định được.
- Nội dung trong tài liệu luôn được xử lý như dữ liệu, không phải system instruction.

