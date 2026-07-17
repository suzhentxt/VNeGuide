# Rubric đánh giá thay đổi

Chấm mỗi hạng mục từ 0 đến 2 trước khi chấp nhận thay đổi.

| Hạng mục | Câu hỏi | Điểm |
| --- | --- | ---: |
| Đúng scope | Thay đổi có bám ba thủ tục trong `data/README.md` không? |  |
| Grounding | Mọi hướng dẫn và rule có truy được về `source_id` không? |  |
| Contract | Enum, field name và output có dùng contract chung không? |  |
| An toàn | LLM có bị ngăn tự đoán dữ liệu hoặc kết luận hành chính không? |  |
| Xác minh | Test/check bắt buộc có thực sự chạy và có bằng chứng không? |  |
| Ranh giới | Business logic có nằm ngoài CLI và provider adapter không? |  |
| Bàn giao | Người tiếp theo có thể tiếp tục từ artifact trong repo không? |  |

## Kết luận

- **Chấp nhận:** không có mục 0 và tổng điểm tối thiểu 12/14.
- **Cần sửa:** có mục 0 hoặc tổng điểm dưới 12.
- **Blocked:** thiếu nguồn, contract hoặc runtime cần thiết để xác minh.

## Bằng chứng review

- Commit/PR:
- Lệnh đã chạy:
- Test hoặc artifact:
- Rủi ro còn lại:
- Bước tiếp theo:
