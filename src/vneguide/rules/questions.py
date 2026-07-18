"""Deterministic next-question selection."""

from __future__ import annotations

from vneguide.data import ProcedureRepository
from vneguide.domain import FieldDefinition, FieldType, ProcedureCode


def field_input_hint(field: FieldDefinition) -> str:
    """Create plain-language input help from reviewed field metadata."""

    field_id = field.field_id
    label = field.label.lower()
    if field.field_type is FieldType.ENUM:
        return "Hãy chọn một phương án bên dưới; tôi sẽ điền vào biểu mẫu sau khi bạn chọn."
    if field.field_type is FieldType.BOOLEAN:
        return "Hãy chọn Có hoặc Không theo đúng trường hợp của bạn."
    if field.field_type is FieldType.DATE:
        return "Nhập ngày theo dạng ngày/tháng/năm, ví dụ 15/04/1990."
    if field.pattern == r"^\d{12}$":
        return (
            "Nhập đủ 12 chữ số, không có khoảng trắng. "
            "Trong bản demo, chỉ sử dụng số giả và không nhập dữ liệu cá nhân thật."
        )
    if "full_name" in field_id:
        return "Nhập đầy đủ họ và tên như trên giấy tờ, ví dụ Nguyễn Văn A."
    if any(marker in field_id for marker in ("residence", "address", "place")):
        return (
            "Ghi địa chỉ đủ để nhận biết: số nhà hoặc thôn/xóm, đường, phường/xã và tỉnh/thành phố."
        )
    if field.field_type in {FieldType.INTEGER, FieldType.NUMBER}:
        minimum = f" từ {field.minimum:g} trở lên" if field.minimum is not None else ""
        return f"Nhập một con số{minimum}; không thêm đơn vị vào ô này."
    return f"Nhập {label} theo thông tin trên giấy tờ hoặc hồ sơ của bạn."


class QuestionSelector:
    def __init__(self, repository: ProcedureRepository) -> None:
        self._repository = repository

    def question_for(self, procedure_code: ProcedureCode | str, field_id: str) -> str:
        field = self._field(procedure_code, field_id)
        if (
            ProcedureCode(procedure_code) is ProcedureCode.BIRTH_CERTIFICATE_COPY
            and field_id == "requester_type"
        ):
            return (
                "Bạn đang xin bản sao cho bản thân, với tư cách người được ủy quyền, "
                "hay đại diện cơ quan/tổ chức? Hãy chọn một phương án bên dưới; "
                "tôi sẽ điền vào biểu mẫu sau khi bạn chọn."
            )
        if field is not None:
            return f"Tiếp theo là mục “{field.label}”. {field_input_hint(field)}"
        return f"Vui lòng bổ sung thông tin cho trường {field_id}."

    def _field(self, procedure_code: ProcedureCode | str, field_id: str) -> FieldDefinition | None:
        return next(
            (
                field
                for field in self._repository.fields_for(procedure_code)
                if field.field_id == field_id
            ),
            None,
        )
