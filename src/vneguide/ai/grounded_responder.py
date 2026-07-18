"""Grounded conversational reply generation.

The responder turns a routing decision and reviewed procedure data into a
natural Vietnamese reply. It is the only place where free-form assistant text
is generated; the structured extractor still owns classification and field
extraction, and the deterministic ``ProcedureQAResponder`` still owns fact
retrieval. The model phrases retrieved facts in natural language but cannot
invent business facts because the reviewed context is the only allowed source.

If the provider call fails, ``respond`` returns ``succeeded=False`` so the
caller can fall back to the deterministic reply and never leave the citizen
without an answer.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from vneguide.ai.prompts import build_conversation_prompt
from vneguide.ai.providers.base import (
    LLMProvider,
    ProviderConfigurationError,
    ProviderError,
    ProviderRefusal,
    ProviderTimeout,
    StructuredRequest,
)
from vneguide.ai.schemas import InformationRequest
from vneguide.data import ProcedureRepository
from vneguide.domain import (
    ChatMessage,
    FieldDefinition,
    FieldType,
    JSONValue,
    ProcedureCode,
    ProcedurePack,
    QATopic,
)
from vneguide.rules import ProcedureQAResponder, QuestionSelector

_REPLY_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "reply": {"type": "string"},
        "off_domain": {"type": "boolean"},
    },
    "required": ["reply", "off_domain"],
}

_MAX_REPLY_CHARS = 800
_MAX_CONTEXT_CHARS = 4_000
_MAX_MESSAGE_CHARS = 2_000
MAX_RESPONDER_HISTORY_TURNS = 6
_MAX_HISTORY_TURNS = MAX_RESPONDER_HISTORY_TURNS


@dataclass(frozen=True, slots=True)
class ResponderContext:
    """Bounded, non-PII context for one conversational reply."""

    user_message: str
    classification: str
    procedure_code: str | None
    information_request: InformationRequest | None
    active_procedure_code: str | None
    pending_procedure_code: str | None
    filled_field_labels: tuple[str, ...]
    missing_field_labels: tuple[str, ...]
    draft_values: Mapping[str, JSONValue]
    recent_turns: tuple[ChatMessage, ...] = ()
    memory_summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.user_message, str) or not self.user_message.strip():
            raise ValueError("user_message must be a non-empty string")
        if len(self.user_message) > _MAX_MESSAGE_CHARS:
            raise ValueError("user_message exceeds the safe length limit")
        if not isinstance(self.classification, str) or not self.classification.strip():
            raise ValueError("classification must be a non-empty string")
        if self.procedure_code is not None and (
            not isinstance(self.procedure_code, str) or not self.procedure_code.strip()
        ):
            raise ValueError("procedure_code must be a short string or None")
        if self.active_procedure_code is not None and (
            not isinstance(self.active_procedure_code, str)
            or not self.active_procedure_code.strip()
        ):
            raise ValueError("active_procedure_code must be a short string or None")
        if self.pending_procedure_code is not None and (
            not isinstance(self.pending_procedure_code, str)
            or not self.pending_procedure_code.strip()
        ):
            raise ValueError("pending_procedure_code must be a short string or None")
        if not isinstance(self.filled_field_labels, tuple):
            raise ValueError("filled_field_labels must be a tuple")
        if not isinstance(self.missing_field_labels, tuple):
            raise ValueError("missing_field_labels must be a tuple")
        if not isinstance(self.draft_values, Mapping):
            raise ValueError("draft_values must be a mapping")
        if not isinstance(self.recent_turns, tuple):
            raise ValueError("recent_turns must be a tuple")
        if any(not isinstance(turn, ChatMessage) for turn in self.recent_turns):
            raise ValueError("recent_turns must contain ChatMessage values")
        if len(self.recent_turns) > _MAX_HISTORY_TURNS:
            raise ValueError(f"recent_turns must contain at most {_MAX_HISTORY_TURNS} messages")
        if not isinstance(self.memory_summary, str):
            raise ValueError("memory_summary must be a string")


@dataclass(frozen=True, slots=True)
class GroundedReply:
    """A grounded reply or a signal to fall back to the deterministic path."""

    text: str | None
    off_domain: bool
    succeeded: bool
    source_ids: tuple[str, ...]


class GroundedResponder:
    """Generate a grounded conversational reply for non-form-driving turns."""

    def __init__(
        self,
        provider: LLMProvider,
        repository: ProcedureRepository,
        *,
        timeout_seconds: float = 20.0,
    ) -> None:
        if (
            type(timeout_seconds) not in (int, float)
            or not math.isfinite(float(timeout_seconds))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive number")
        self._provider = provider
        self._repository = repository
        self._qa = ProcedureQAResponder(repository)
        self._questions = QuestionSelector(repository)
        self._timeout_seconds = timeout_seconds

    def respond(self, context: ResponderContext) -> GroundedReply:
        """Return a grounded reply, or ``succeeded=False`` to trigger fallback."""

        reviewed_context, source_ids = self._reviewed_context(context)
        conversation_context = self._conversation_context(context)
        system_prompt = build_conversation_prompt(
            reviewed_context=reviewed_context,
            conversation_context=conversation_context,
            recent_turns=context.recent_turns,
            memory_summary=context.memory_summary,
        )
        request = StructuredRequest(
            system_prompt=system_prompt,
            user_prompt=context.user_message[:_MAX_MESSAGE_CHARS],
            json_schema=_REPLY_SCHEMA,
            schema_name="vneguide_conversation",
            timeout_seconds=self._timeout_seconds,
        )
        try:
            raw = self._provider.generate_structured(request)
        except (ProviderConfigurationError, ProviderRefusal, ProviderTimeout, ProviderError):
            return _fallback_reply(source_ids)
        text, off_domain = _decode_reply(raw)
        if text is None:
            return _fallback_reply(source_ids)
        return GroundedReply(
            text=text[:_MAX_REPLY_CHARS],
            off_domain=off_domain,
            succeeded=True,
            source_ids=source_ids,
        )

    def _reviewed_context(self, context: ResponderContext) -> tuple[str, tuple[str, ...]]:
        """Retrieve reviewed facts to ground the reply, or an empty block."""

        if context.classification != "informational":
            return "", ()
        request = context.information_request
        if request is None:
            return "", ()
        code = self._resolve_code(context)
        if code is None:
            return "", ()
        if QATopic.FIELD_HELP in request.topics:
            return self._field_help_context(code, request, context.draft_values)
        answer = self._qa.answer(code, request, draft_values=context.draft_values)
        return answer.text, answer.source_ids

    def _field_help_context(
        self,
        code: ProcedureCode,
        request: InformationRequest,
        draft_values: Mapping[str, JSONValue],
    ) -> tuple[str, tuple[str, ...]]:
        """Ground field-help replies with reviewed help text or field type."""

        answer = self._qa.answer(code, request, draft_values=draft_values)
        pack = self._repository.get_by_code(code)
        field = _find_field(pack, request.target_field_id)
        if field is not None and not field.help_text:
            hint = _format_hint(field)
            if hint:
                return f"{answer.text} {hint}", answer.source_ids
        return answer.text, answer.source_ids

    def _resolve_code(self, context: ResponderContext) -> ProcedureCode | None:
        for candidate in (
            context.procedure_code,
            context.active_procedure_code,
            context.pending_procedure_code,
        ):
            if candidate is None:
                continue
            try:
                return ProcedureCode(candidate)
            except ValueError:
                return None
        return None

    def _conversation_context(self, context: ResponderContext) -> str:
        parts: list[str] = []
        if context.pending_procedure_code is not None:
            name = self._procedure_label(context.pending_procedure_code)
            parts.append(f"Thủ tục đang chờ xác nhận: {name}. Người dùng vừa nói chưa xác nhận.")
        elif context.active_procedure_code is not None:
            name = self._procedure_label(context.active_procedure_code)
            parts.append(f"Thủ tục đang làm: {name}.")
            if context.filled_field_labels:
                parts.append("Đã điền: " + _join_labels(context.filled_field_labels) + ".")
            if context.missing_field_labels:
                parts.append("Còn thiếu: " + _join_labels(context.missing_field_labels) + ".")
        else:
            parts.append("Chưa chọn thủ tục; người dùng mới bắt đầu hoặc đang social talk.")
        text = " ".join(parts)
        return text[:_MAX_CONTEXT_CHARS]

    def _procedure_label(self, code: str) -> str:
        try:
            return self._questions.procedure_label(ProcedureCode(code))
        except ValueError:
            return code


def _fallback_reply(source_ids: tuple[str, ...]) -> GroundedReply:
    return GroundedReply(text=None, off_domain=False, succeeded=False, source_ids=source_ids)


def _decode_reply(raw: object) -> tuple[str | None, bool]:
    """Decode the provider payload into a reply string and off-domain flag."""

    if not isinstance(raw, Mapping):
        return None, False
    reply = raw.get("reply")
    off_domain = raw.get("off_domain")
    if not isinstance(reply, str) or not reply.strip():
        return None, False
    if not isinstance(off_domain, bool):
        off_domain = False
    return reply.strip(), off_domain


def _find_field(pack: ProcedurePack, field_id: str | None) -> FieldDefinition | None:
    if field_id is None:
        return None
    return next((field for field in pack.fields if field.field_id == field_id), None)


def _format_hint(field: FieldDefinition) -> str:
    """Return a plain-Vietnamese format hint derived from the field type."""

    if field.field_type is FieldType.DATE:
        return "Anh/chị nhập đầy đủ ngày/tháng/năm sinh (ví dụ 01/01/1990) ạ."
    if field.field_type is FieldType.INTEGER:
        return "Anh/chị nhập một số nguyên ạ."
    if field.field_type is FieldType.NUMBER:
        return "Anh/chị nhập một số ạ."
    if field.field_type is FieldType.BOOLEAN:
        return 'Anh/chị trả lời "Có" hoặc "Không" ạ.'
    if field.field_type is FieldType.ENUM:
        return "Anh/chị chọn một trong các lựa chọn đã liệt kê ạ."
    return ""


def _join_labels(labels: tuple[str, ...]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return "; ".join(labels[:-1]) + f"; và {labels[-1]}"


# Re-export for callers that import from this module.
__all__ = [
    "GroundedReply",
    "GroundedResponder",
    "InformationRequest",
    "MAX_RESPONDER_HISTORY_TURNS",
    "ResponderContext",
]


# Validate JSON encoding eagerly so a bad schema never reaches the provider at
# runtime. This mirrors the defensive posture of the structured extractor.
try:
    json.dumps(dict(_REPLY_SCHEMA), ensure_ascii=False)
except (TypeError, ValueError) as _exc:  # pragma: no cover - schema is a literal
    raise RuntimeError("conversation reply schema is not JSON-serializable") from _exc
