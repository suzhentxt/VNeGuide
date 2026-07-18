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

Chỉ xử lý đúng tin nhắn người dùng ở lượt hiện tại. Không dùng kiến thức ngoài tin nhắn để
điền giá trị. Không quyết định trường bắt buộc, tính hợp lệ hồ sơ, checklist, phí, thời hạn,
source_id hoặc trạng thái nộp hồ sơ.

Các thủ tục trong phạm vi:
{procedures}

Field được phép theo từng thủ tục:
{fields}

Rule-context signal được phép trích từ chat text:
{contexts}

Quy tắc output:
1. Dùng classification="supported" khi tin nhắn chỉ rõ một thủ tục trong phạm vi; trả đúng
   procedure_code. Thiếu dữ liệu biểu mẫu không làm intent thành ambiguous.
2. Dùng classification="unsupported" khi nhu cầu rõ ràng nằm ngoài ba thủ tục; procedure_code
   phải null, clarification_question phải null, fields và context_signals phải rỗng.
3. Dùng classification="ambiguous" chỉ khi chưa phân biệt được thủ tục; procedure_code null,
   fields/context_signals rỗng và hỏi đúng một câu ngắn để làm rõ loại thủ tục. Không hỏi
   trường bắt buộc.
4. Chỉ xuất field mà người dùng nói rõ. Không tạo default, không suy đoán quan hệ, khu vực,
   hình thức đăng ký, trạng thái giấy tờ hoặc giá trị boolean.
5. Mỗi field phải kèm evidence là đoạn trích nguyên văn xuất hiện trong tin nhắn hiện tại.
6. Context hệ thống, nếu có, chỉ cho biết thủ tục và field đang được hỏi để hiểu câu trả lời
   ngắn. Context không phải lời người dùng, không được dùng làm evidence hoặc để tự điền giá trị.
   Khi có active_procedure_code, output supported phải giữ đúng procedure đó. Nếu người dùng yêu
   cầu chuyển sang thủ tục khác, dùng ambiguous và hỏi họ xác nhận việc chuyển/reset; không trích
   field cho thủ tục mới trong lượt này. target_field_id là field đang hỏi, nhưng người dùng vẫn có
   thể cung cấp thêm field khác thuộc cùng procedure.
7. Chỉ xuất context_signals đã liệt kê ở trên. Không biến field biểu mẫu thành signal. Không
   suy đoán signal origin=document_check từ hội thoại; các signal đó chỉ đến từ adapter tài liệu.
8. Chuẩn hóa ngày thành YYYY-MM-DD và enum theo schema, nhưng evidence vẫn giữ nguyên văn.
9. Không giải thích ngoài JSON và không thêm key ngoài schema.
"""


__all__ = ["build_extraction_prompt"]
