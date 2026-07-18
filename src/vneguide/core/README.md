# Core

Owner trong kế hoạch tích hợp hiện tại: Người 2.

Core điều phối hội thoại nhiều lượt và không phụ thuộc terminal/web. Public factory mặc định là `vneguide.core:create_session`.

Luồng dữ liệu:

1. Structured extractor phân loại thủ tục và trả field có evidence.
2. Core tạo `FieldSuggestion` trạng thái `pending`; không tự ghi vào draft.
3. `accept_suggestion`, `reject_suggestion`, `edit_suggestion` hoặc `edit_field` cập nhật state.
4. Rule engine xác định field thiếu, validation issue và bước tiếp theo.

Biến thể `guided` (mặc định) thêm `CatalogReplyComposer`. Với route đã seed thủ tục và câu hỏi thuần
guidance khớp whole-message allowlist, composer trả lời trước extraction nên không phụ thuộc provider.
Câu có field, thủ tục khác hoặc nội dung hỗn hợp vẫn chạy structured extractor trước khi composer
được dùng. Bảy topic được phép là phí, thời gian, hồ sơ, các bước, cơ quan, kênh nộp và kết quả. Fact
được render từ `service_info`, `checklist` hoặc `guidance_steps`; không dùng model/RAG và không được
tự tạo fact. Một lượt chỉ trả tối đa một topic.

Guidance-only trả `present_guidance`, không tăng clarification attempt và không đổi draft/revision.
Lượt vừa hỏi guidance vừa có field hợp lệ vẫn tạo suggestion `pending`. Sau `unsupported`,
`ambiguous`, đổi thủ tục hoặc lỗi provider, core không dùng ngữ cảnh thủ tục ngầm cho lượt guidance
tiếp theo; người dùng phải nhắc rõ thủ tục hoặc extractor xác nhận lại. Mọi `source_id` do composer
trả phải thuộc procedure pack đang hoạt động, nếu không core bỏ reply đó và dùng baseline.

Rollback/A-B bằng `VNEGUIDE_CHAT_CORE_VARIANT=baseline`; wire contract FastAPI/Next.js không đổi.

`CaseDraft.values` chỉ chứa giá trị đã Accept/Edit hoặc sửa trực tiếp từ form. Mọi mutation
suggestion/form phải gửi `expected_revision`; mutation hợp lệ tăng revision đúng một lần. Tin nhắn
chat không đổi form revision và dùng `client_turn_id` để chống gửi trùng; reset tạo session ID mới.

Field sửa trực tiếp được đánh dấu đồng thời `confirmed` và `dirty`. Extractor không được tạo đề xuất
ghi đè field `dirty`. Field đã confirmed chỉ được mở lại thành suggestion cần review khi câu hiện tại
có ngôn ngữ correction rõ ràng như “địa chỉ đúng là…” hoặc “đổi thành…”. Core hỏi tối đa hai lần cho
một field; sau hai câu trả lời không hiểu, lời đáp chuyển sang nhập trực tiếp trên biểu mẫu.

Wire contract tiếp tục dùng một trường string `next_action`. Vocabulary cố định là:
`confirm_procedure`, `choose_portal`, `fill_missing_field`, `review_suggestion`, `upload_document`,
`fix_validation`, `ready_to_continue`, `needs_official_review`, `unsupported`. Mỗi lượt chỉ có một
hành động chính. Các tên enum Python cũ chỉ còn là alias tương thích và không tạo thêm wire value.

Unit test inject extractor/repository; không gọi model thật và không cần API key.
