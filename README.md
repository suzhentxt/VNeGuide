# Trợ lý AI thủ tục hành chính Hà Nội

Kho tài liệu đặc tả cho một trợ lý AI hỗ trợ công dân chuẩn bị và tự kiểm tra hồ sơ hành chính trước khi nộp.

MVP tập trung vào ba thủ tục tại Hà Nội:

1. Đăng ký khai sinh.
2. Đăng ký thường trú.
3. Cấp giấy phép xây dựng mới cho nhà ở riêng lẻ.

## Bộ tài liệu

| Tài liệu | Nội dung |
|---|---|
| [Product spec](docs/01-product-spec.md) | Mục tiêu, phạm vi, yêu cầu chức năng, UX và tiêu chí nghiệm thu |
| [User stories](docs/02-user-stories.md) | Bốn path chính và acceptance criteria |
| [AI Product Canvas & failure modes](docs/03-ai-product-canvas.md) | Thiết kế sản phẩm AI, rủi ro và cơ chế kiểm soát |
| [Architecture & API](docs/04-architecture-api.md) | Kiến trúc, dữ liệu, model, API và widget integration |
| [OpenAPI contract](docs/openapi.yaml) | Contract máy đọc được cho public REST API |
| [Prototype research & prompt test](docs/05-research-prompt-test.md) | Kế hoạch nghiên cứu, bộ test, prompt contracts và quy trình chọn prompt |
| [Evaluation & ROI](docs/06-evaluation-roi.md) | Chỉ số chất lượng, UX, hiệu năng, an toàn và mô hình ROI |
| [One-page summary](docs/07-one-page-summary.md) | Bản tóm tắt một trang dùng cho pitch/submission |
| [Source register](docs/08-source-register.md) | Nguồn dữ liệu chính thức, metadata và quy trình cập nhật |

## Nguyên tắc sản phẩm

- Rule-first: quy định, checklist và lỗi bắt buộc do rule engine quyết định; LLM không tự tạo quy định.
- Citation-first: mọi hướng dẫn hành chính đều có nguồn và ngày kiểm chứng.
- Human confirmation: người dùng xác nhận dữ liệu trích xuất từ ảnh/PDF trước khi kiểm tra.
- Privacy-by-default: demo chỉ dùng dữ liệu mẫu, không lưu hồ sơ hoặc nội dung tài liệu.
- Honest boundary: kết quả là kiểm tra trước khi nộp, không phải quyết định chấp thuận của cơ quan nhà nước.
