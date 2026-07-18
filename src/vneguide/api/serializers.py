"""Explicit conversion from wire-neutral domain objects to HTTP DTOs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from pydantic import JsonValue as PydanticJsonValue

from vneguide.data import ProcedureRepository
from vneguide.domain import CaseDraft, FieldType, JSONValue, ProcedureCode, TurnResult

from .schemas import (
    ChatMessageResponse,
    ChatTurnResponse,
    DraftResponse,
    MissingFieldResponse,
    ProcedureResponse,
    SourceResponse,
    SuggestionResponse,
    ValidationIssueResponse,
    ValidationResponse,
)


def json_value(value: JSONValue) -> PydanticJsonValue:
    if isinstance(value, Mapping):
        return cast(PydanticJsonValue, {key: json_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return cast(PydanticJsonValue, [json_value(item) for item in value])
    return cast(PydanticJsonValue, value)


class TurnResultSerializer:
    def __init__(self, repository: ProcedureRepository) -> None:
        self._repository = repository

    def serialize(self, result: TurnResult) -> ChatTurnResponse:
        code = result.state.draft.procedure_code
        labels = self._field_labels(code)
        fields = (
            {field.field_id: field for field in self._repository.fields_for(code)}
            if code is not None
            else {}
        )
        procedure = self._procedure(code)
        validation = result.validation
        return ChatTurnResponse(
            reply=result.reply,
            next_action=result.next_action.value,
            procedure=procedure,
            draft=self.serialize_draft(result.state.draft),
            messages=[
                ChatMessageResponse(role=message.role.value, content=message.content)
                for message in result.state.messages
            ],
            suggestions=[
                SuggestionResponse(
                    id=item.suggestion_id,
                    field_id=item.field_id,
                    label=labels.get(item.field_id, item.field_id),
                    current_value=json_value(item.current_value),
                    suggested_value=json_value(item.suggested_value),
                    evidence=item.evidence,
                    status=item.status.value,
                    revision=item.revision,
                )
                for item in result.suggestions
            ],
            missing_fields=[
                MissingFieldResponse(
                    field_id=field_id,
                    label=labels.get(field_id, field_id),
                    choices=(
                        [json_value(value) for value in fields[field_id].values]
                        if fields[field_id].field_type is FieldType.ENUM
                        else [True, False]
                        if fields[field_id].field_type is FieldType.BOOLEAN
                        else []
                    ),
                )
                for field_id in result.missing_fields
            ],
            validation=(
                None
                if validation is None
                else ValidationResponse(
                    status=validation.status.value,
                    readiness_score=validation.readiness_score,
                    issues=[
                        ValidationIssueResponse(
                            rule_id=issue.rule_id,
                            severity=issue.severity.value,
                            message=issue.message,
                            field_id=issue.field_id,
                            suggestion=issue.suggestion,
                            source_ids=list(issue.source_ids),
                        )
                        for issue in validation.issues
                    ],
                )
            ),
            sources=[self._source(source_id) for source_id in result.source_ids],
        )

    def serialize_draft(self, draft: CaseDraft) -> DraftResponse:
        return DraftResponse(
            values={field_id: json_value(value) for field_id, value in draft.values.items()},
            revision=draft.revision,
            confirmed_fields=sorted(draft.confirmed_fields),
            dirty_fields=sorted(draft.dirty_fields),
            pack_version=draft.pack_version,
        )

    def _field_labels(self, code: ProcedureCode | None) -> dict[str, str]:
        if code is None:
            return {}
        return {field.field_id: field.label for field in self._repository.fields_for(code)}

    def _procedure(self, code: ProcedureCode | None) -> ProcedureResponse | None:
        if code is None:
            return None
        pack = self._repository.get_by_code(code)
        return ProcedureResponse(code=code.value, name=pack.procedure_name)

    def _source(self, source_id: str) -> SourceResponse:
        source = self._repository.get_source(source_id)
        return SourceResponse(
            id=source.source_id,
            title=source.title,
            publisher=source.publisher,
            url=source.url,
            verified_at=source.verified_at,
        )
