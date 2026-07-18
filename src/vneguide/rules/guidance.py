"""Deterministic answers built only from the reviewed procedure package."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol

from vneguide.data import ProcedureRepository
from vneguide.domain import (
    FieldDefinition,
    FieldType,
    IssueSeverity,
    JSONValue,
    ProcedureCode,
    ProcedurePack,
    QATopic,
)

from .questions import QuestionSelector


class InformationRequestView(Protocol):
    """Structural view of the AI routing result; it contains no answer text."""

    @property
    def topics(self) -> tuple[QATopic, ...]: ...

    @property
    def target_field_id(self) -> str | None: ...

    @property
    def reference_fields(self) -> Mapping[str, object]: ...


@dataclass(frozen=True, slots=True)
class QAAnswer:
    """A grounded answer and the reviewed sources used to render it."""

    text: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("QA answer text must not be empty")
        if not self.source_ids:
            raise ValueError("QA answer must cite at least one reviewed source")


@dataclass(frozen=True, slots=True)
class _Section:
    heading: str
    text: str
    source_ids: tuple[str, ...]


_TOPIC_HEADINGS = {
    QATopic.FEE: "Lệ phí",
    QATopic.PROCESSING_TIME: "Thời gian giải quyết",
    QATopic.DOCUMENTS: "Hồ sơ, giấy tờ",
    QATopic.REQUIRED_INFORMATION: "Thông tin cần khai",
    QATopic.AUTHORITY: "Cơ quan giải quyết",
    QATopic.CHANNELS: "Kênh nộp",
    QATopic.RESULT: "Kết quả",
    QATopic.STEPS: "Các bước thực hiện",
    QATopic.LEGAL_BASIS: "Nguồn và căn cứ",
    QATopic.CONDITIONS_LIMITED: "Phạm vi và điều kiện",
    QATopic.FIELD_HELP: "Giải thích mục trên biểu mẫu",
}

_BASE_REQUIRED_REQUIREMENTS = frozenset(
    {
        "required",
        "required_for_lookup",
        "required_for_area_check",
        "required_for_threshold",
        "required_declaration",
        "required_or_identity_document",
    }
)


class ProcedureQAResponder:
    """Render reviewed facts without calling or retaining an LLM provider."""

    def __init__(self, repository: ProcedureRepository) -> None:
        self._repository = repository
        self._questions = QuestionSelector(repository)

    def answer(
        self,
        procedure_code: ProcedureCode | str,
        request: InformationRequestView,
        *,
        draft_values: Mapping[str, JSONValue] | None = None,
    ) -> QAAnswer:
        code = ProcedureCode(procedure_code)
        pack = self._repository.get_by_code(code)
        values = {} if draft_values is None else draft_values
        sections = tuple(
            self._render_topic(pack, topic, request, values) for topic in request.topics
        )
        source_ids = _unique(source_id for section in sections for source_id in section.source_ids)
        if len(sections) == 1:
            text = f"Dạ, {sections[0].text}"
        else:
            text = "Dạ, em gửi anh/chị các thông tin đã được duyệt:\n\n" + "\n\n".join(
                f"{section.heading}: {section.text}" for section in sections
            )
        return QAAnswer(text=text, source_ids=source_ids)

    def _render_topic(
        self,
        pack: ProcedurePack,
        topic: QATopic,
        request: InformationRequestView,
        values: Mapping[str, JSONValue],
    ) -> _Section:
        renderers = {
            QATopic.FEE: self._fee,
            QATopic.PROCESSING_TIME: self._processing_time,
            QATopic.DOCUMENTS: self._documents,
            QATopic.REQUIRED_INFORMATION: self._required_information,
            QATopic.AUTHORITY: self._authority,
            QATopic.CHANNELS: self._channels,
            QATopic.RESULT: self._result,
            QATopic.STEPS: self._steps,
            QATopic.LEGAL_BASIS: self._legal_basis,
            QATopic.CONDITIONS_LIMITED: self._conditions_limited,
            QATopic.FIELD_HELP: self._field_help,
        }
        text, source_ids = renderers[topic](pack, request, values)
        return _Section(_TOPIC_HEADINGS[topic], text, source_ids)

    def _fee(
        self,
        pack: ProcedurePack,
        request: InformationRequestView,
        values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        sources = pack.service_info_sources["fee"]
        fee_info = self._mapping(pack.service_info.get("fee"))
        if pack.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY:
            amount = _format_vnd(fee_info.get("amount_vnd"))
            if amount is None:
                return self._missing_fact(pack), sources
            return (
                f"mức tham chiếu là {amount} cho thủ tục cấp bản sao Giấy khai sinh. "
                "VNeGuide không tự nhân mức này theo số bản; anh/chị kiểm tra lại số tiền "
                "ở bước nộp chính thức ạ.",
                sources,
            )
        if pack.procedure_code is ProcedureCode.HOUSING_CONDITION_CONFIRMATION:
            display = fee_info.get("display")
            if not isinstance(display, str) or not display.strip():
                return self._missing_fact(pack), sources
            return (
                f"thủ tục xác nhận điều kiện nhà ở {display[:1].lower() + display[1:]} ạ.",
                sources,
            )

        mode = self._reference_value(request, values, "registration_mode")
        channel = self._reference_value(request, values, "submission_channel")
        individual = self._mapping(fee_info.get("individual_or_household"))
        by_list = self._mapping(fee_info.get("by_list"))
        lines: list[str] = []
        if mode in (None, "individual_or_household"):
            if channel in (None, "online"):
                amount = _format_vnd(individual.get("online_vnd"))
                if amount is not None:
                    lines.append(f"cá nhân/hộ gia đình nộp trực tuyến: {amount}/lần đăng ký")
            if channel in (None, "direct"):
                amount = _format_vnd(individual.get("direct_vnd"))
                if amount is not None:
                    lines.append(f"cá nhân/hộ gia đình nộp trực tiếp: {amount}/lần đăng ký")
        if mode in (None, "by_list"):
            if channel in (None, "online"):
                amount = _format_vnd(by_list.get("online_vnd_per_person"))
                if amount is not None:
                    lines.append(f"theo danh sách nộp trực tuyến: {amount}/người")
            if channel in (None, "direct"):
                amount = _format_vnd(by_list.get("direct_vnd_per_person"))
                if amount is not None:
                    lines.append(f"theo danh sách nộp trực tiếp: {amount}/người")
            lines.append(
                "trường hợp theo danh sách cần kiểm tra mức thu chính thức với cơ quan tiếp nhận"
            )
        if mode in (None, "armed_forces"):
            authority = pack.service_info.get("authority")
            authority_text = (
                authority
                if isinstance(authority, str) and authority.strip()
                else "cơ quan tiếp nhận"
            )
            lines.append(
                "dữ liệu đã duyệt chưa có mức phí riêng cho trường hợp tại đơn vị lực lượng "
                f"vũ trang; anh/chị cần hỏi {authority_text} hoặc cơ quan tiếp nhận"
            )
        if not lines:
            return self._missing_fact(pack), sources
        exemption = fee_info.get("exemption")
        if isinstance(exemption, str) and exemption.strip():
            lines.append(exemption.rstrip("."))
        return "; ".join(lines) + ".", sources

    def _processing_time(
        self,
        pack: ProcedurePack,
        _request: InformationRequestView,
        _values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        value = pack.service_info.get("processing_time_display")
        if not isinstance(value, str) or not value.strip():
            return self._missing_fact(pack), pack.service_info_sources["authority"]
        return f"thời gian được công bố trong package là {value} ạ.", pack.service_info_sources[
            "processing_time_display"
        ]

    def _documents(
        self,
        pack: ProcedurePack,
        _request: InformationRequestView,
        _values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        required = []
        by_channel = []
        conditional = []
        source_ids: list[str] = []
        for item in pack.checklist:
            if item.requirement == "required_for_lookup":
                continue
            rendered = item.name
            if item.condition.strip():
                rendered += f" ({item.condition.rstrip('.')})"
            if item.requirement == "required":
                required.append(rendered)
            elif item.requirement in {"required_by_channel", "conditional_postal"}:
                by_channel.append(rendered)
            else:
                conditional.append(rendered)
            source_ids.extend(item.source_ids)
        sections = []
        if required:
            sections.append("Bắt buộc: " + _join_items(required))
        if by_channel:
            sections.append("Theo kênh nộp: " + _join_items(by_channel))
        if conditional:
            sections.append("Tùy trường hợp: " + _join_items(conditional))
        if not sections:
            return self._missing_fact(pack), pack.service_info_sources["authority"]
        return " ".join(sections), _unique(source_ids)

    def _required_information(
        self,
        pack: ProcedurePack,
        _request: InformationRequestView,
        _values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        required: list[str] = []
        conditional: list[str] = []
        sources: list[str] = []
        for field in pack.fields:
            if field.requirement in _BASE_REQUIRED_REQUIREMENTS:
                required.append(field.label)
            elif field.requirement.startswith("conditional"):
                conditional.append(field.label)
            else:
                continue
            sources.extend(field.source_ids)
        text = "Thông tin cần khai: " + _join_items(required) + "."
        if conditional:
            text += " Tùy trường hợp cần thêm: " + _join_items(conditional) + "."
        text += " Đây là các mục dữ liệu trên biểu mẫu, không phải danh sách giấy tờ ạ."
        return text, _unique(sources)

    def _authority(
        self,
        pack: ProcedurePack,
        _request: InformationRequestView,
        _values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        value = pack.service_info.get("authority")
        if not isinstance(value, str) or not value.strip():
            return self._missing_fact(pack), pack.service_info_sources["authority"]
        return f"cơ quan giải quyết là {value} ạ.", pack.service_info_sources["authority"]

    def _channels(
        self,
        pack: ProcedurePack,
        _request: InformationRequestView,
        _values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        channels = self._sequence(pack.service_info.get("channels"))
        if not channels:
            return self._missing_fact(pack), pack.service_info_sources["authority"]
        labels = [self._questions.choice_label(channel) for channel in channels]
        return f"anh/chị có thể nộp {_join_items(labels)} ạ.", pack.service_info_sources["channels"]

    def _result(
        self,
        pack: ProcedurePack,
        _request: InformationRequestView,
        _values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        value = pack.service_info.get("result")
        if not isinstance(value, str) or not value.strip():
            return self._missing_fact(pack), pack.service_info_sources["authority"]
        return f"kết quả được công bố là: {value} ạ.", pack.service_info_sources["result"]

    def _steps(
        self,
        pack: ProcedurePack,
        _request: InformationRequestView,
        _values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        if not pack.guidance_steps:
            return self._missing_fact(pack), pack.service_info_sources["authority"]
        text = " ".join(f"Bước {item.step}: {item.text}" for item in pack.guidance_steps)
        return text, _unique(
            source_id for item in pack.guidance_steps for source_id in item.source_ids
        )

    def _legal_basis(
        self,
        pack: ProcedurePack,
        _request: InformationRequestView,
        _values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        sources = self._repository.resolve_sources(pack.source_ids)
        titles = [source.title for source in sources]
        if pack.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY:
            lead = (
                "package hiện chưa có văn bản pháp luật riêng cho thủ tục này; nguồn đã duyệt "
                "hiện có là "
            )
        else:
            lead = "các nguồn đã được duyệt trong package gồm "
        return lead + _join_items(titles) + ".", pack.source_ids

    def _conditions_limited(
        self,
        pack: ProcedurePack,
        _request: InformationRequestView,
        _values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        scope = pack.scope
        in_scope = [item for item in self._sequence(scope.get("in_scope")) if isinstance(item, str)]
        official = [
            item
            for item in self._sequence(scope.get("needs_official_review"))
            if isinstance(item, str)
        ]
        conditional = [
            f"{item.name}: {item.condition}"
            for item in pack.checklist
            if item.requirement.startswith("conditional")
        ]
        reviewed_rules = [
            rule.message
            for rule in pack.validation_rules
            if rule.severity is IssueSeverity.NEEDS_REVIEW
        ]
        pieces = []
        if in_scope:
            pieces.append("VNeGuide chỉ hỗ trợ trong phạm vi: " + _join_items(in_scope) + ".")
        review_items = official + reviewed_rules
        if review_items:
            pieces.append(
                "Cần cơ quan có thẩm quyền kiểm tra chính thức khi: "
                + _join_items(review_items)
                + "."
            )
        if conditional:
            pieces.append(
                "Tùy trường hợp, checklist yêu cầu thêm: " + _join_items(conditional) + "."
            )
        pieces.append(
            "VNeGuide không kết luận anh/chị đủ điều kiện và không thay cơ quan có thẩm quyền."
        )
        return " ".join(pieces), pack.source_ids

    def _field_help(
        self,
        pack: ProcedurePack,
        request: InformationRequestView,
        _values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        field = self._field(pack, request.target_field_id)
        if field is None:
            return self._missing_fact(pack), pack.service_info_sources["authority"]
        pieces = []
        if field.help_text:
            pieces.append(field.help_text.rstrip(".") + ".")
        selected = request.reference_fields.get(field.field_id)
        if isinstance(selected, str) and selected in field.choice_help:
            pieces.append(
                f"{self._questions.choice_label(selected).capitalize()}: "
                f"{field.choice_help[selected]}"
            )
        elif field.choice_help:
            pieces.append(
                "Các lựa chọn: "
                + " ".join(
                    f"{self._questions.choice_label(value).capitalize()}: {text}"
                    for value, text in field.choice_help.items()
                )
            )
        elif field.field_type is FieldType.ENUM:
            labels = [self._questions.choice_label(value) for value in field.values]
            pieces.append(f"Mục {field.label} có {len(labels)} lựa chọn: {_join_items(labels)}.")
        if not pieces:
            return self._missing_fact(pack), pack.service_info_sources["authority"]
        return " ".join(pieces), field.source_ids

    @staticmethod
    def _field(pack: ProcedurePack, field_id: str | None) -> FieldDefinition | None:
        if field_id is None:
            return None
        return next((field for field in pack.fields if field.field_id == field_id), None)

    @staticmethod
    def _reference_value(
        request: InformationRequestView,
        values: Mapping[str, JSONValue],
        field_id: str,
    ) -> object:
        if field_id in request.reference_fields:
            return request.reference_fields[field_id]
        return values.get(field_id)

    @staticmethod
    def _mapping(value: JSONValue | None) -> Mapping[str, JSONValue]:
        return value if isinstance(value, Mapping) else {}

    @staticmethod
    def _sequence(value: JSONValue | None) -> tuple[JSONValue, ...]:
        if isinstance(value, (list, tuple)):
            return tuple(value)
        return ()

    @staticmethod
    def _missing_fact(pack: ProcedurePack) -> str:
        authority = pack.service_info.get("authority")
        if not isinstance(authority, str) or not authority.strip():
            authority = "cơ quan có thẩm quyền"
        return (
            "dữ liệu đã duyệt của VNeGuide chưa có thông tin này. Anh/chị vui lòng liên hệ "
            f"{authority} hoặc xem nguồn chính thức ạ."
        )


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _join_items(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    return f"{'; '.join(values[:-1])}; và {values[-1]}"


def _format_vnd(value: object) -> str | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return f"{value:,}".replace(",", ".") + " đồng"
