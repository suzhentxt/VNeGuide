"""Deterministic next-question selection."""

from __future__ import annotations

from vneguide.data import ProcedureRepository
from vneguide.domain import FieldType, JSONValue, ProcedureCode

_PROCEDURE_LABELS = {
    ProcedureCode.BIRTH_CERTIFICATE_COPY: "cấp bản sao Giấy khai sinh",
    ProcedureCode.HOUSING_CONDITION_CONFIRMATION: (
        "xác nhận điều kiện nhà ở để đăng ký thường trú"
    ),
    ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION: "đăng ký tạm trú",
}

# The catalog remains authoritative for which values are allowed. This map only
# turns those stable machine values into plain Vietnamese for conversation UI.
_ENUM_VALUE_LABELS = {
    "self": "cá nhân tự yêu cầu",
    "authorized_person": "người được ủy quyền",
    "organization": "đại diện tổ chức",
    "citizen_id": "căn cước công dân",
    "identity_card": "chứng minh nhân dân",
    "passport": "hộ chiếu",
    "identity_certificate": "giấy chứng nhận căn cước",
    "electronic_identity": "căn cước điện tử",
    "online": "trực tuyến",
    "direct": "trực tiếp",
    "postal": "qua bưu chính",
    "grandparent": "ông hoặc bà",
    "parent": "cha hoặc mẹ",
    "child": "con",
    "spouse": "vợ hoặc chồng",
    "sibling": "anh, chị hoặc em ruột",
    "other": "khác",
    "inner_city": "nội thành Hà Nội",
    "suburban": "ngoại thành Hà Nội",
    "individual_or_household": "cá nhân hoặc hộ gia đình",
    "by_list": "theo danh sách",
    "armed_forces": "đơn vị lực lượng vũ trang",
    "owned": "sở hữu",
    "rented": "thuê",
    "borrowed": "mượn",
    "accommodated": "ở nhờ",
    "join_family_household": "về ở cùng hộ gia đình",
}
_BOOLEAN_QUESTIONS = {
    (
        ProcedureCode.HOUSING_CONDITION_CONFIRMATION,
        "declared_stable_use",
    ): (
        "Anh/chị xác nhận chỗ ở hiện đang được sử dụng ổn định, đúng không ạ? "
        "Anh/chị trả lời Có hoặc Không giúp em."
    ),
    (
        ProcedureCode.HOUSING_CONDITION_CONFIRMATION,
        "declared_no_dispute",
    ): (
        "Anh/chị xác nhận nhà/đất hiện không có tranh chấp, đúng không ạ? "
        "Anh/chị trả lời Có hoặc Không giúp em."
    ),
    (
        ProcedureCode.HOUSING_CONDITION_CONFIRMATION,
        "declared_not_prohibited_location",
    ): (
        "Anh/chị xác nhận chỗ ở không thuộc địa điểm bị cấm đăng ký thường trú mới, "
        "đúng không ạ? Anh/chị trả lời Có hoặc Không giúp em."
    ),
    (
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        "applicant_is_minor",
    ): (
        "Người đăng ký có phải là người chưa thành niên không ạ? "
        "Anh/chị trả lời Có hoặc Không giúp em."
    ),
    (
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        "minor_consent_present",
    ): (
        "Đã có ý kiến đồng ý của cha, mẹ hoặc người giám hộ chưa ạ? "
        "Anh/chị trả lời Có hoặc Không giúp em."
    ),
    (
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        "legal_dwelling_data_retrievable",
    ): (
        "Thông tin chỗ ở hợp pháp có tra cứu được từ cơ sở dữ liệu không ạ? "
        "Anh/chị trả lời Có hoặc Không giúp em."
    ),
    (
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        "legal_dwelling_document_present",
    ): (
        "Anh/chị có giấy tờ chứng minh chỗ ở hợp pháp không ạ? "
        "Anh/chị trả lời Có hoặc Không giúp em."
    ),
    (
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        "owner_or_householder_consent",
    ): (
        "Khi cần, anh/chị đã có sự đồng ý của chủ hộ hoặc chủ sở hữu chưa ạ? "
        "Anh/chị trả lời Có hoặc Không giúp em."
    ),
    (
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        "fee_exemption_claimed",
    ): ("Anh/chị có đề nghị miễn lệ phí không ạ? Anh/chị trả lời Có hoặc Không giúp em."),
}


class QuestionSelector:
    def __init__(self, repository: ProcedureRepository) -> None:
        self._repository = repository

    def question_for(self, procedure_code: ProcedureCode | str, field_id: str) -> str:
        for field in self._repository.fields_for(procedure_code):
            if field.field_id == field_id:
                if field.field_type is FieldType.ENUM:
                    choices = tuple(
                        _ENUM_VALUE_LABELS[value]
                        for value in field.values
                        if isinstance(value, str) and value in _ENUM_VALUE_LABELS
                    )
                    if len(choices) == len(field.values):
                        return f"Anh/chị chọn {field.label.lower()}: {_join_choices(choices)} ạ?"
                if field.field_type is FieldType.BOOLEAN:
                    question = _BOOLEAN_QUESTIONS.get(
                        (ProcedureCode(procedure_code), field.field_id)
                    )
                    if question is not None:
                        return question
                    return "Anh/chị vui lòng chọn Có hoặc Không trên biểu mẫu giúp em ạ."
                return f"Anh/chị cho em biết {field.label.lower()} ạ."
        return "Anh/chị vui lòng bổ sung thông tin còn thiếu trên biểu mẫu giúp em ạ."

    def procedure_label(self, procedure_code: ProcedureCode | str) -> str:
        """Return the centralized short label used in conversational prompts."""

        return _PROCEDURE_LABELS[ProcedureCode(procedure_code)]

    def choice_label(self, value: JSONValue) -> str:
        """Return a plain-language label without exposing a raw enum token."""

        if isinstance(value, str):
            return _ENUM_VALUE_LABELS.get(value, value.replace("_", " "))
        return str(value)


def _join_choices(choices: tuple[str, ...]) -> str:
    if len(choices) == 1:
        return choices[0]
    return f"{', '.join(choices[:-1])} hoặc {choices[-1]}"
