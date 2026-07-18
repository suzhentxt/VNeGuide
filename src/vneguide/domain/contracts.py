"""Wire-neutral contracts shared by AI, core, rules, and CLI."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .enums import MessageRole, NextAction, ProcedureCode, QATopic
from .models import FieldSuggestion, JSONValue, ValidationResult, freeze_mapping


@dataclass(frozen=True, slots=True)
class CaseDraft:
    """A generic draft that supports all approved procedure packs."""

    procedure_code: ProcedureCode | None = None
    values: Mapping[str, JSONValue] = field(default_factory=dict)
    confirmed_fields: frozenset[str] = field(default_factory=frozenset)
    dirty_fields: frozenset[str] = field(default_factory=frozenset)
    revision: int = 0
    pack_version: str | None = None

    def __post_init__(self) -> None:
        if self.revision < 0:
            raise ValueError("draft revision must not be negative")
        value_fields = set(self.values)
        unknown_confirmed = self.confirmed_fields - value_fields
        unknown_dirty = self.dirty_fields - value_fields
        if unknown_confirmed:
            raise ValueError(f"confirmed fields have no value: {sorted(unknown_confirmed)}")
        if unknown_dirty:
            raise ValueError(f"dirty fields have no value: {sorted(unknown_dirty)}")
        unconfirmed_dirty = self.dirty_fields - self.confirmed_fields
        if unconfirmed_dirty:
            raise ValueError(f"dirty fields are not confirmed: {sorted(unconfirmed_dirty)}")
        object.__setattr__(self, "values", freeze_mapping(self.values))
        object.__setattr__(self, "confirmed_fields", frozenset(self.confirmed_fields))
        object.__setattr__(self, "dirty_fields", frozenset(self.dirty_fields))


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: MessageRole
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("message content must not be empty")


@dataclass(frozen=True, slots=True)
class ConversationState:
    draft: CaseDraft = field(default_factory=CaseDraft)
    pending_procedure_code: ProcedureCode | None = None
    messages: tuple[ChatMessage, ...] = ()
    turn_number: int = 0
    clarification_attempts: Mapping[str, int] = field(default_factory=dict)
    suggestions: tuple[FieldSuggestion, ...] = ()
    asked_question_ids: tuple[str, ...] = ()
    recent_information_procedure_code: ProcedureCode | None = None
    recent_information_topics: tuple[QATopic, ...] = ()
    memory_summary: str = ""

    def __post_init__(self) -> None:
        if self.turn_number < 0:
            raise ValueError("turn_number must not be negative")
        if self.pending_procedure_code is not None and self.draft.procedure_code is not None:
            raise ValueError("pending procedure cannot coexist with an active procedure")
        if any(attempts < 0 for attempts in self.clarification_attempts.values()):
            raise ValueError("clarification attempts must not be negative")
        if any(not question_id.strip() for question_id in self.asked_question_ids):
            raise ValueError("asked question IDs must not be empty")
        if len(set(self.asked_question_ids)) != len(self.asked_question_ids):
            raise ValueError("asked question IDs must be unique")
        if (
            len(self.recent_information_topics) > 3
            or len(set(self.recent_information_topics)) != len(self.recent_information_topics)
            or any(not isinstance(topic, QATopic) for topic in self.recent_information_topics)
        ):
            raise ValueError(
                "recent information topics must contain at most three unique QATopic values"
            )
        if (self.recent_information_procedure_code is None) != (not self.recent_information_topics):
            raise ValueError("recent information procedure and topics must be recorded together")
        if not isinstance(self.memory_summary, str):
            raise ValueError("memory_summary must be a string")
        object.__setattr__(self, "messages", tuple(self.messages))
        object.__setattr__(
            self,
            "clarification_attempts",
            MappingProxyType(dict(self.clarification_attempts)),
        )
        object.__setattr__(self, "suggestions", tuple(self.suggestions))
        object.__setattr__(self, "asked_question_ids", tuple(self.asked_question_ids))
        object.__setattr__(
            self,
            "recent_information_topics",
            tuple(self.recent_information_topics),
        )


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    procedure_code: ProcedureCode | None
    fields: Mapping[str, JSONValue] = field(default_factory=dict)
    confidence: float = 0.0
    needs_clarification: bool = False
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "fields", freeze_mapping(self.fields))
        object.__setattr__(self, "warnings", tuple(self.warnings))


@dataclass(frozen=True, slots=True)
class TurnRequest:
    message: str
    state: ConversationState = field(default_factory=ConversationState)

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("turn message must not be empty")


@dataclass(frozen=True, slots=True)
class TurnResult:
    reply: str
    state: ConversationState
    next_action: NextAction
    source_ids: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    validation: ValidationResult | None = None
    extracted_fields: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.reply.strip():
            raise ValueError("turn reply must not be empty")
        object.__setattr__(self, "source_ids", tuple(self.source_ids))
        object.__setattr__(self, "missing_fields", tuple(self.missing_fields))
        object.__setattr__(self, "extracted_fields", freeze_mapping(self.extracted_fields))

    @property
    def procedure_type(self) -> str:
        code = self.state.draft.procedure_code
        if code is not None:
            return code.value
        if self.validation is not None:
            return self.validation.status.value
        if self.next_action is NextAction.OUT_OF_SCOPE:
            return "out_of_scope"
        return "chưa xác định"

    @property
    def draft(self) -> Mapping[str, JSONValue]:
        return self.state.draft.values

    @property
    def validation_issues(self) -> tuple[object, ...]:
        return () if self.validation is None else self.validation.issues

    @property
    def suggestions(self) -> tuple[FieldSuggestion, ...]:
        return self.state.suggestions
