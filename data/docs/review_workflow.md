# VNeGuide – Quy trình review dữ liệu và procedure pack v2

## 1. Nguyên tắc nguồn
1. Nguồn A1/A1-LOCAL quyết định tên thủ tục, checklist, thời hạn, phí và điều kiện.
2. Văn bản A2 được dùng để diễn giải và xây rule khi đã xác định đúng hiệu lực.
3. Dataset Hugging Face chỉ dùng discovery/RAG seed; mọi requirement runtime phải có source ID A1/A2.
4. Blog, diễn đàn và nội dung do LLM sinh không được dùng làm nguồn quy tắc.

## 2. Trạng thái pack
- `draft`: đang chuẩn hóa.
- `needs_review`: còn mâu thuẫn hoặc thiếu nguồn.
- `approved`: được phép chạy runtime.
- `stale`: quá hạn review hoặc nguồn thay đổi.
- `retired`: không dùng nữa.

## 3. Versioning
- MAJOR: thay phạm vi, schema hoặc căn cứ pháp lý làm thay đổi hành vi.
- MINOR: thêm field/rule có tương thích ngược.
- PATCH: sửa câu chữ, source URL hoặc lỗi không đổi hành vi.

## 4. Review gate
- Domain & Data Lead kiểm tra source trace và điều kiện.
- Product & UX Lead kiểm tra câu chữ, flow và trạng thái cuối.
- AI & Evaluation Lead kiểm tra rule có thể đánh giá và LLM không được tự bổ sung quy định.
- Architecture & Delivery Lead chỉ merge pack `approved` và validate schema.

## 5. Chu kỳ
- Demo/hackathon: kiểm chứng lại trong 24 giờ trước demo.
- Pilot: review mỗi 30 ngày và ngay khi nguồn chính thức thay đổi.
- Mọi pack quá `next_review_at` tự chuyển `stale`.

Ngày kiểm chứng bản này: 2026-07-17.
