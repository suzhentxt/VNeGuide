"""Validated HTTP request and response shapes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionContext(StrictModel):
    procedure_code: str | None = Field(default=None, max_length=32)
    procedure_title: str | None = Field(default=None, max_length=200)
    route: str | None = Field(default=None, max_length=500)


class CreateSessionRequest(StrictModel):
    context: SessionContext | None = None
    memory_scope_token: str | None = Field(
        default=None,
        min_length=32,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
        exclude=True,
    )


class MessageRequest(StrictModel):
    message: str = Field(min_length=1, max_length=4_000)
    client_turn_id: str | None = Field(default=None, min_length=1, max_length=100)


class SuggestionActionRequest(StrictModel):
    action: Literal["accept", "reject", "edit"]
    value: JsonValue = None
    expected_revision: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def require_edit_value(self) -> SuggestionActionRequest:
        if self.action == "edit" and "value" not in self.model_fields_set:
            raise ValueError("value is required when action is edit")
        return self


class FieldEditRequest(StrictModel):
    value: JsonValue
    expected_revision: int = Field(ge=0, strict=True)
    interaction: Literal["form", "chat_choice"] = "form"
    display_label: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def require_chat_choice_label(self) -> FieldEditRequest:
        if self.interaction == "chat_choice" and self.display_label is None:
            raise ValueError("display_label is required for chat_choice")
        return self


class ChatMessageResponse(StrictModel):
    role: str
    content: str


class ProcedureResponse(StrictModel):
    code: str
    name: str


class SuggestionResponse(StrictModel):
    id: str
    field_id: str
    label: str
    current_value: JsonValue
    suggested_value: JsonValue
    evidence: str
    status: str
    revision: int


class MissingFieldResponse(StrictModel):
    field_id: str
    label: str
    field_type: Literal["string", "date", "integer", "number", "boolean", "enum"]
    input_hint: str
    choices: list[JsonValue] = Field(default_factory=list)


class ValidationIssueResponse(StrictModel):
    rule_id: str
    severity: str
    message: str
    field_id: str | None
    suggestion: str
    source_ids: list[str]


class ValidationResponse(StrictModel):
    status: str
    readiness_score: int | None
    issues: list[ValidationIssueResponse]


class SourceResponse(StrictModel):
    id: str
    title: str
    publisher: str
    url: str
    verified_at: str


class DraftResponse(StrictModel):
    values: dict[str, JsonValue]
    revision: int
    confirmed_fields: list[str]
    dirty_fields: list[str]
    pack_version: str | None


class ChatTurnResponse(StrictModel):
    reply: str
    next_action: str
    procedure: ProcedureResponse | None
    draft: DraftResponse
    messages: list[ChatMessageResponse]
    suggestions: list[SuggestionResponse]
    missing_fields: list[MissingFieldResponse]
    validation: ValidationResponse | None
    sources: list[SourceResponse]


class SessionResponse(StrictModel):
    expires_in_seconds: int
    context: SessionContext | None
    context_supported: bool
    scope_warning: str | None
    draft: DraftResponse
    turn: ChatTurnResponse | None


class HealthResponse(StrictModel):
    status: Literal["ok"] = "ok"


class ErrorDetail(StrictModel):
    code: str
    message: str
    retryable: bool = False


class ErrorResponse(StrictModel):
    error: ErrorDetail
