"""Vietnamese structured-extraction prompt contract."""

from __future__ import annotations

from vneguide.ai.schemas import ExtractionCatalog


def build_extraction_prompt(catalog: ExtractionCatalog) -> str:
    """Build a routing/slot prompt using reviewed procedure metadata only."""

    procedure_lines: list[str] = []
    field_lines: list[str] = []
    context_lines: list[str] = []
    for procedure in catalog.procedures:
        aliases = ", ".join(procedure.aliases) if procedure.aliases else "không có"
        in_scope = "; ".join(procedure.in_scope) if procedure.in_scope else "không khai báo"
        review_scope = (
            "; ".join(procedure.needs_official_review)
            if procedure.needs_official_review
            else "không có"
        )
        out_of_scope = (
            "; ".join(procedure.out_of_scope) if procedure.out_of_scope else "không khai báo"
        )
        procedure_lines.append(
            f"- {procedure.code}: {procedure.name}. Cụm gợi ý: {aliases}. "
            f"Trong phạm vi: {in_scope}. Vẫn route vào thủ tục nhưng cần review chính thức: "
            f"{review_scope}. Ngoài phạm vi: {out_of_scope}."
        )
        rendered_fields = []
        for field in catalog.fields_for(procedure.code):
            type_hint = field.field_type
            if field.values:
                type_hint = f"enum[{', '.join(field.values)}]"
            rendered_fields.append(f"{field.field_id} ({field.label}; {type_hint})")
        field_lines.append(f"- {procedure.code}: " + "; ".join(rendered_fields))
        rendered_contexts = []
        for item in catalog.extractable_rule_contexts_for(procedure.code):
            type_hint = item.field_type
            if item.values:
                type_hint = f"enum[{', '.join(item.values)}]"
            rendered_contexts.append(
                f"{item.input_id} ({item.label}; {type_hint}; origin={item.origin})"
            )
        if rendered_contexts:
            context_lines.append(f"- {procedure.code}: " + "; ".join(rendered_contexts))

    procedures = "\n".join(procedure_lines)
    fields = "\n".join(field_lines)
    contexts = "\n".join(context_lines) or "- Không có signal nào được phép từ chat text."
    return f"""Bạn là bộ phân loại nhu cầu và trích xuất dữ liệu có cấu trúc cho VNeGuide.

User prompt là JSON có `current_user_message` và `conversation_context`. Context chỉ gồm
mã thủ tục đang hoạt động và field mà core đang chờ; đây là metadata tham chiếu,
không phải evidence. Dùng context để hiểu câu trả lời rút gọn nhưng chỉ điền giá trị
được nói rõ trong `current_user_message`. Không quyết định trường bắt buộc, tính hợp lệ
hồ sơ, checklist, phí, thời hạn, source_id hoặc trạng thái nộp hồ sơ.

Các thủ tục trong phạm vi:
{procedures}

Field được phép theo từng thủ tục:
{fields}

Rule-context signal được phép trích từ chat text:
{contexts}

Quy tắc output:
1. Dùng classification="supported" khi câu hiện tại chỉ rõ một thủ tục trong phạm vi hoặc
   là câu trả lời rút gọn phù hợp với `active_procedure_code`; trả đúng procedure_code.
   Thiếu dữ liệu biểu mẫu không làm intent thành ambiguous.
2. Dùng classification="unsupported" khi nhu cầu rõ ràng nằm ngoài ba thủ tục; procedure_code
   phải null, clarification_question phải null, fields và context_signals phải rỗng.
3. Chỉ dùng classification="ambiguous" khi không có `active_procedure_code` và chưa phân biệt
   được thủ tục. Giữ fields/context_signals rỗng và đặt `clarification_question` thành đúng một
   câu hỏi ngắn, tự nhiên để làm rõ loại thủ tục.
   Khi đã có `active_procedure_code` nhưng câu hiện tại liên quan đến thủ tục mà không đủ rõ để
   trích bất kỳ field/context signal nào, giữ classification="supported", giữ các mảng rỗng và
   dùng `clarification_question` để phản hồi thân thiện, nhắc lại ngắn gọn điều đã hiểu rồi hỏi
   đúng `expected_field_id`. Không dùng câu máy móc, không nhắc tên field kỹ thuật và không bịa
   dữ liệu. Nếu đã trích được bất kỳ giá trị nào thì `clarification_question` phải null.
4. Chỉ xuất field mà người dùng nói rõ. Không tạo default, không suy đoán quan hệ, khu vực,
   hình thức đăng ký, trạng thái giấy tờ hoặc giá trị boolean.
   Đại từ xưng hô như "tôi", "mình", "chúng tôi" hoặc "con tôi" không phải họ tên.
   Chỉ trích field họ tên khi người dùng nêu một tên riêng cụ thể.
5. Mỗi field phải kèm evidence là đoạn trích nguyên văn xuất hiện trong tin nhắn hiện tại.
6. Context hệ thống chỉ cho biết `active_procedure_code` và `expected_field_id` để hiểu câu trả lời
   ngắn. Context không phải lời người dùng, không được dùng làm evidence hoặc để tự điền giá trị.
   `expected_field_id` chỉ là gợi ý; vẫn được trích field khác khi câu hiện tại nói rõ field đó.
7. Chỉ xuất context_signals đã liệt kê ở trên. Không biến field biểu mẫu thành signal. Không
   suy đoán signal origin=document_check từ hội thoại; signal đó chỉ đến từ adapter tài liệu.
8. Chuẩn hóa ngày thành YYYY-MM-DD và enum theo schema, nhưng evidence vẫn giữ nguyên văn.
9. Nếu câu hiện tại nêu rõ một thủ tục khác trong phạm vi, ưu tiên ý định mới để core xác nhận
   việc chuyển dịch vụ và vô hiệu hóa dữ liệu nháp cũ. Chỉ trả unsupported khi người dùng nêu
   rõ một dịch vụ hoặc thủ tục nằm ngoài phạm vi. Lời chào, cảm ơn và trò chuyện xã giao không
   phải nhu cầu thủ tục ngoài phạm vi; core sẽ xử lý riêng và không được dùng chúng để điền field.
10. Không dùng nội dung context làm evidence. Không giải thích ngoài JSON và không thêm key
    ngoài schema.

Ví dụ bắt buộc để phân biệt field:
- Context thủ tục 1.004194 đang chờ `registration_mode`, câu hiện tại "tôi đăng ký online":
  giữ procedure_code 1.004194 và chỉ trích `submission_channel="online"`. Không suy ra
  `registration_mode`; online/trực tuyến là kênh nộp, không phải hình thức cá nhân/danh sách.
- Context thủ tục 2.000635, câu hiện tại "cho con tôi": giữ procedure_code 2.000635,
  fields rỗng. Không suy ra `requester_type`, quan hệ ủy quyền hoặc họ tên.
- Câu "xin cấp bản sao giấy khai sinh đi": procedure_code 2.000635, fields rỗng.
"""


__all__ = ["build_extraction_prompt"]
