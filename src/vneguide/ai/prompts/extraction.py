"""Vietnamese structured-extraction prompt contract."""

from __future__ import annotations

from vneguide.ai.schemas import ExtractionCatalog


def build_extraction_prompt(catalog: ExtractionCatalog) -> str:
    """Build a routing/slot prompt using reviewed procedure metadata only."""

    procedure_lines: list[str] = []
    field_lines: list[str] = []
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

    procedures = "\n".join(procedure_lines)
    fields = "\n".join(field_lines)
    return f"""Bạn là bộ phân loại nhu cầu và trích xuất dữ liệu có cấu trúc cho VNeGuide.

Chỉ xử lý đúng tin nhắn người dùng ở lượt hiện tại. Không dùng kiến thức ngoài tin nhắn để
điền giá trị. Không quyết định trường bắt buộc, tính hợp lệ hồ sơ, checklist, phí, thời hạn,
source_id hoặc trạng thái nộp hồ sơ.

Các thủ tục trong phạm vi:
{procedures}

Field được phép theo từng thủ tục:
{fields}

Quy tắc output:
1. Dùng classification="supported" khi tin nhắn chỉ rõ một thủ tục trong phạm vi; trả đúng
   procedure_code. Thiếu dữ liệu biểu mẫu không làm intent thành ambiguous.
2. Dùng classification="unsupported" khi nhu cầu rõ ràng nằm ngoài ba thủ tục; procedure_code
   phải null, clarification_question phải null và fields phải rỗng.
3. Dùng classification="ambiguous" chỉ khi chưa phân biệt được thủ tục; procedure_code null,
   fields rỗng và hỏi đúng một câu ngắn để làm rõ loại thủ tục. Không hỏi trường bắt buộc.
4. Chỉ xuất field mà người dùng nói rõ. Không tạo default, không suy đoán quan hệ, khu vực,
   hình thức đăng ký, trạng thái giấy tờ hoặc giá trị boolean.
5. Mỗi field phải kèm evidence là đoạn trích nguyên văn xuất hiện trong tin nhắn hiện tại.
6. Chuẩn hóa ngày thành YYYY-MM-DD và enum theo schema, nhưng evidence vẫn giữ nguyên văn.
7. Không giải thích ngoài JSON và không thêm key ngoài schema.
"""


__all__ = ["build_extraction_prompt"]
