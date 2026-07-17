# Product Specification

## 1. Tầm nhìn

Trợ lý AI giúp công dân hiểu đúng thủ tục, chuẩn bị đủ giấy tờ và phát hiện lỗi cơ bản trước khi nộp hồ sơ. Sản phẩm được nhúng trực tiếp vào cổng dịch vụ công qua widget hoặc REST API, không yêu cầu cài ứng dụng mới.

Tên làm việc: **Hành Chính Dễ**.

## 2. Bài toán và người dùng

### Vấn đề

- Công dân không biết chính xác cần làm thủ tục nào, chuẩn bị giấy tờ gì và nộp ở đâu.
- Sai sót chỉ được phát hiện khi cán bộ tiếp nhận hồ sơ.
- Câu hỏi lặp lại gây quá tải hỗ trợ và làm phát sinh nhiều lượt đi lại.

### Người dùng chính

- Công dân Hà Nội có kỹ năng số thấp hoặc trung bình.
- Người thân hỗ trợ công dân chuẩn bị hồ sơ.
- Nhân viên một cửa muốn giảm thời gian giải thích các lỗi phổ biến.

### Jobs-to-be-done

> Khi cần làm một thủ tục hành chính, tôi muốn biết chính xác mình phải chuẩn bị và sửa gì để có thể nộp hồ sơ với ít lần đi lại nhất.

## 3. Phạm vi MVP

### Trong phạm vi

- Đăng ký khai sinh.
- Đăng ký thường trú.
- Cấp giấy phép xây dựng mới cho nhà ở riêng lẻ.
- Địa bàn pilot: Hà Nội.
- Guided intake bằng tiếng Việt tự nhiên.
- Checklist hồ sơ và hướng dẫn từng bước có ví dụ, citation và ngày kiểm chứng.
- Kiểm tra form có cấu trúc cùng ảnh/PDF mẫu.
- Widget iframe, demo web và REST API có OpenAPI.

### Ngoài phạm vi

- Nộp hồ sơ thật hoặc thanh toán lệ phí.
- Đăng nhập VNeID, ký số hoặc truy cập cơ sở dữ liệu dân cư.
- Kết luận hồ sơ chắc chắn được chấp thuận.
- Tư vấn pháp lý cho tranh chấp hoặc ngoại lệ phức tạp.
- Tỉnh/thành khác và thủ tục ngoài ba thủ tục pilot.
- Lưu trữ hồ sơ hoặc dữ liệu cá nhân.

## 4. Luồng trải nghiệm tối thiểu

1. Người dùng nhập nhu cầu bằng câu tự nhiên.
2. Hệ thống xác định thủ tục hoặc hỏi tối đa 3–5 câu làm rõ.
3. Người dùng xác nhận thủ tục AI đã hiểu.
4. Hệ thống hiển thị checklist, quy trình, cơ quan, thời gian, lệ phí, ví dụ và nguồn.
5. Người dùng điền form hoặc tải tối đa 10 trang JPEG/PNG/PDF, tổng dung lượng tối đa 10 MB.
6. AI trích xuất dữ liệu kèm bằng chứng và confidence.
7. Người dùng xác nhận hoặc sửa dữ liệu trích xuất.
8. Rule engine và semantic checker tạo báo cáo lỗi.
9. Người dùng sửa dữ liệu và chạy kiểm tra lại.

## 5. Yêu cầu chức năng

### FR-01 — Nhận diện nhu cầu

- Nhận câu mô tả tự do bằng tiếng Việt, kể cả typo phổ biến.
- Trả về một trong ba `procedure_id` hoặc `unsupported`.
- Hiển thị cách hệ thống hiểu nhu cầu và cho phép đổi thủ tục.
- Không tiếp tục tự động nếu confidence dưới ngưỡng 0,75.

### FR-02 — Hỏi làm rõ

- Câu hỏi chỉ được sinh từ danh sách discriminator của procedure pack.
- Không hỏi lại thông tin đã trả lời.
- Mỗi câu hỏi phải giải thích ngắn gọn tại sao cần thông tin đó.
- Nếu người dùng không biết, cho phép chọn “Tôi không chắc” và chuyển kết quả sang `needs_review` khi cần.

### FR-03 — Hướng dẫn theo trường hợp

`ProcedureGuide` phải có:

- Tên và mã thủ tục.
- Đối tượng/điều kiện áp dụng.
- Hồ sơ bắt buộc và hồ sơ có điều kiện.
- Số lượng bản chính/bản sao nếu nguồn quy định.
- Trình tự từng bước và ví dụ minh họa.
- Cơ quan tiếp nhận, hình thức nộp, thời gian và lệ phí.
- Cảnh báo cho ngoại lệ chưa được MVP hỗ trợ.
- Source citation, `source_version` và `last_verified_at`.

Không được hiển thị một yêu cầu hồ sơ nếu yêu cầu đó không liên kết tới `rule_id` và `source_id` đã được duyệt.

### FR-04 — Trích xuất tài liệu

- Hỗ trợ JPEG, PNG và PDF; từ chối file không đúng magic bytes.
- Trả về `value`, `evidence`, `page`, `confidence` cho từng trường.
- Trường không đọc được phải trả `null`, không suy đoán.
- Người dùng phải xác nhận dữ liệu trước khi validation.
- Không ghi file vào disk/object storage hoặc application logs.

### FR-05 — Kiểm tra trước khi nộp

Kiểm tra bốn nhóm lỗi:

1. Thiếu trường hoặc thiếu tài liệu bắt buộc.
2. Sai định dạng/phạm vi, ví dụ ngày không hợp lệ hoặc số định danh sai độ dài.
3. Vi phạm điều kiện, ví dụ thiếu giấy tờ phát sinh từ một lựa chọn đã xác nhận.
4. Xung đột giữa form và tài liệu, ví dụ họ tên hoặc địa chỉ không nhất quán.

Mỗi issue phải có mức độ, trường liên quan, giải thích dễ hiểu, bằng chứng, cách sửa, rule và nguồn.

### FR-06 — Trạng thái kết quả

- `pass`: “Không phát hiện lỗi trong phạm vi kiểm tra”.
- `needs_fix`: có lỗi rõ ràng người dùng có thể sửa.
- `needs_review`: dữ liệu mơ hồ, ngoại lệ hoặc cần cán bộ xác minh.

Không dùng các nhãn “hồ sơ hợp lệ”, “được duyệt” hoặc cam kết kết quả hành chính.

### FR-07 — Tích hợp

- Widget được nhúng bằng một script và hiển thị trong iframe sandboxed.
- Hỗ trợ cấu hình `apiBase`, theme, ngôn ngữ và procedure mặc định.
- `postMessage` chỉ phát sự kiện `ready`, `completed`, `error`; không chứa PII.
- API có OpenAPI, CORS allowlist, rate limit và request ID.

## 6. Yêu cầu phi chức năng

- Mobile-first; hoạt động từ chiều rộng 360 px.
- Hỗ trợ bàn phím, focus rõ, label cho screen reader và contrast WCAG AA.
- Câu ngắn, từ phổ thông; thuật ngữ pháp lý có giải thích.
- p95 guided response không quá 6 giây; extraction/check không quá 20 giây.
- API error rate dưới 2% trong demo test.
- Không lưu PII; telemetry chỉ gồm procedure, rule version, latency, error code và feedback tổng quát.
- Khi model lỗi, hiển thị hướng dẫn đã chuẩn hóa nếu có và cho phép thử extraction lại.

## 7. Tiêu chí hoàn thành MVP

- Bốn user-story paths trong tài liệu user stories chạy end-to-end trên public URL.
- Ba procedure packs được hai reviewer duyệt.
- Mọi requirement trong guidance có citation hợp lệ.
- Gold test và ngưỡng eval trong tài liệu Evaluation & ROI đạt yêu cầu.
- Widget chạy trên demo portal và một host origin thứ hai.
- README, architecture diagram, API contract, source register và one-page summary hoàn chỉnh.

