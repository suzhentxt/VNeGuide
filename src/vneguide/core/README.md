# Core

Owner: Người 3.

Core điều phối hội thoại nhiều lượt và không phụ thuộc terminal/web. Public factory mặc định là `vneguide.core:create_session`.

Luồng dữ liệu:

1. Structured extractor phân loại thủ tục và trả field có evidence.
2. Core tạo `FieldSuggestion` trạng thái `pending`; không tự ghi vào draft.
3. `accept_suggestion`, `reject_suggestion` hoặc `edit_suggestion` cập nhật state.
4. Rule engine xác định field thiếu, validation issue và bước tiếp theo.

`CaseDraft.values` chỉ chứa giá trị đã Accept hoặc Edit. Revision ngăn suggestion cũ ghi đè bản nháp mới. Sau hai lần không thu được field đang hỏi, core chuyển `manual_input`.

Unit test inject extractor/repository; không gọi model thật và không cần API key.
