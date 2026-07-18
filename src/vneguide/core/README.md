# Core

Owner trong kế hoạch tích hợp hiện tại: Người 2.

Core điều phối hội thoại nhiều lượt và không phụ thuộc terminal/web. Public factory mặc định là `vneguide.core:create_session`.

Luồng dữ liệu:

1. Structured extractor phân loại thủ tục và trả field có evidence.
2. Core tạo `FieldSuggestion` trạng thái `pending`; không tự ghi vào draft.
3. `accept_suggestion`, `reject_suggestion`, `edit_suggestion` hoặc `edit_field` cập nhật state.
4. Rule engine xác định field thiếu, validation issue và bước tiếp theo.

Biến thể `guided` (mặc định) thêm `CatalogReplyComposer` sau bước extraction. Composer chỉ nhận mã
thủ tục đã khóa và tin nhắn hiện tại để nhận diện bảy topic allowlist: phí, thời gian, hồ sơ, các
bước, cơ quan, kênh nộp và kết quả. Fact được render từ `service_info`, `checklist` hoặc
`guidance_steps`; không dùng model/RAG và không được tự tạo fact. Một lượt chỉ trả tối đa một topic.

Guidance-only trả `present_guidance`, không tăng clarification attempt và không đổi draft/revision.
Lượt vừa hỏi guidance vừa có field hợp lệ vẫn tạo suggestion `pending`. `unsupported`, `ambiguous`,
đổi thủ tục và lỗi composer đi theo flow fail-closed sẵn có. Mọi `source_id` do composer trả phải
thuộc procedure pack đang hoạt động, nếu không core bỏ reply đó và dùng baseline.

Rollback/A-B bằng `VNEGUIDE_CHAT_CORE_VARIANT=baseline`; wire contract FastAPI/Next.js không đổi.

`CaseDraft.values` chỉ chứa giá trị đã Accept/Edit hoặc sửa trực tiếp từ form. Mọi mutation
suggestion/form phải gửi `expected_revision`; mutation hợp lệ tăng revision đúng một lần. Tin nhắn
chat không đổi form revision và dùng `client_turn_id` để chống gửi trùng; reset tạo session ID mới.

Field sửa trực tiếp được đánh dấu đồng thời `confirmed` và `dirty`. Extractor không được tạo đề xuất
ghi đè field đã confirmed/dirty. `asked_question_ids` ngăn core phát lại cùng câu hỏi; khi field đã
được hỏi nhưng vẫn thiếu, core chuyển sang `manual_input` để form tiếp tục hoạt động độc lập với AI.

Unit test inject extractor/repository; không gọi model thật và không cần API key.
