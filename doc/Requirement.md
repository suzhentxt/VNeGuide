# Đề bài Hackathon

## Vấn đề

Khi người dân cần thực hiện một thủ tục hành chính như xin giấy phép xây dựng, đăng ký hộ khẩu hoặc làm giấy khai sinh, họ thường gặp ba trở ngại gây khó khăn:

1. **Không biết cần chuẩn bị những gì:** Người dân không rõ cần có những giấy tờ, biểu mẫu nào hoặc phải đến cơ quan nào để thực hiện thủ tục.
2. **Không biết thông tin đã được điền chính xác hay chưa:** Người dân thường chỉ phát hiện sai sót sau khi hồ sơ đã được cán bộ tiếp nhận và kiểm tra.
3. **Hệ thống hỗ trợ bị quá tải:** Số lượng câu hỏi quá lớn trong khi số cán bộ hỗ trợ có hạn, khiến người dân phải đi lại trực tiếp nhiều lần.

## Sản phẩm cần xây dựng

Xây dựng một giải pháp AI có ba nhóm khả năng chính:

### 1. Hướng dẫn tiếp nhận nhu cầu

Người dùng mô tả nhu cầu của mình bằng ngôn ngữ tự nhiên. AI sẽ:

- Đặt các câu hỏi làm rõ thông tin.
- Cung cấp danh sách giấy tờ cụ thể cần chuẩn bị.
- Hướng dẫn quy trình thực hiện theo từng bước.
- Đưa ra ví dụ minh họa cho từng bước.

### 2. Kiểm tra trước khi nộp hồ sơ

Người dùng nhập các thông tin đã điền trong hồ sơ. AI sẽ:

- Phát hiện các lỗi thường gặp.
- Phát hiện trường thông tin còn thiếu.
- Phát hiện dữ liệu mâu thuẫn hoặc không nhất quán.
- Đề xuất cách sửa trước khi hồ sơ được nộp chính thức.

### 3. Tích hợp liền mạch

Giải pháp phải có khả năng nhúng trực tiếp vào các cổng dịch vụ công hiện có thông qua **API, widget hoặc chatbot**, để người dân không cần cài đặt thêm một ứng dụng mới.

## Sản phẩm cần bàn giao

### 1. Bản demo hoạt động thực tế

- Có thể truy cập qua một URL công khai.
- Phải là sản phẩm hoạt động được, không phải bản thiết kế mô phỏng.
- Luồng người dùng tối thiểu phải bao gồm:
  1. Nhập nhu cầu cần giải quyết.
  2. Nhận hướng dẫn theo từng bước.
  3. Kiểm tra các thông tin đã điền trong hồ sơ.

### 2. Tài liệu kiến trúc hệ thống

Tài liệu cần bao gồm:

- Sơ đồ kiến trúc hệ thống.
- Thông tin chi tiết về các mô hình AI được sử dụng.
- Thông tin chi tiết về các API được sử dụng.

### 3. Bản tóm tắt một trang

Bản tóm tắt cần trình bày:

- Vấn đề cần giải quyết.
- Giải pháp đề xuất.
- Nhóm người dùng mục tiêu.
- Lộ trình triển khai.

### 4. Nguồn dữ liệu

Dữ liệu phải đến từ các nguồn thủ tục hành chính công khai, bao gồm:

- [Cổng Dịch vụ công Quốc gia](https://dichvucong.gov.vn/).
- Danh mục biểu mẫu thủ tục hành chính được phân loại theo từng lĩnh vực.

## Tiêu chí đánh giá

Giải pháp sẽ được đánh giá dựa trên bốn tiêu chí:

1. **Độ chính xác và đầy đủ:** Nội dung hướng dẫn phải phù hợp với các quy định hiện hành.
2. **Khả năng kiểm tra hồ sơ:** Hệ thống có thể phát hiện hiệu quả các lỗi và thông tin còn thiếu trong hồ sơ người dùng đã điền.
3. **Tính khả thi khi tích hợp:** Giải pháp có khả năng tích hợp vào các hệ thống dịch vụ công hiện có và đưa ra được một lộ trình thí điểm cụ thể.
4. **Trải nghiệm người dùng:** Sản phẩm phải dễ sử dụng đối với người dân không có kiến thức chuyên môn về công nghệ.
