"""Suggestion-aware conversation session independent of terminal I/O."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import replace
from typing import Protocol

from vneguide.ai import ExtractionOutcome, ExtractionTurnContext, StructuredExtractor
from vneguide.data import ProcedureRepository
from vneguide.domain import (
    CaseDraft,
    ChatMessage,
    ConversationState,
    FieldSuggestion,
    JSONValue,
    MessageRole,
    NextAction,
    ProcedureCode,
    SuggestionStatus,
    TurnResult,
    ValidationResult,
    ValidationStatus,
)
from vneguide.rules import QuestionSelector, RuleEngine


class Extractor(Protocol):
    def extract(
        self,
        message: str,
        *,
        context: ExtractionTurnContext | None = None,
    ) -> ExtractionOutcome: ...


class RevisionConflictError(ValueError):
    """A client mutation targets an older draft revision."""


class ProcedureNotSelectedError(ValueError):
    """A form mutation cannot be validated before selecting a procedure."""


class ProcedureConflictError(ValueError):
    """A requested procedure conflicts with the active session procedure."""


class ConversationSession:
    """Own one ephemeral conversation and its confirmed draft."""

    def __init__(self, extractor: Extractor, repository: ProcedureRepository) -> None:
        self._extractor = extractor
        self._repository = repository
        self._rules = RuleEngine(repository)
        self._questions = QuestionSelector(repository)
        self._state = ConversationState()
        self._closed = False

    @property
    def state(self) -> ConversationState:
        return self._state

    def initialize_procedure(self, procedure_code: ProcedureCode | str) -> None:
        """Seed a pristine route-scoped session without changing form revision zero."""

        self._ensure_open()
        code = ProcedureCode(procedure_code)
        current = self._state.draft.procedure_code
        if current is code:
            return
        if current is not None or self._state.turn_number or self._state.suggestions:
            raise ProcedureConflictError("Conversation already has an active procedure")
        pack = self._repository.get_by_code(code)
        self._state = replace(
            self._state,
            draft=replace(
                self._state.draft,
                procedure_code=code,
                pack_version=pack.version,
            ),
        )

    def send(self, message: str) -> TurnResult:
        self._ensure_open()
        active_code = self._state.draft.procedure_code
        previous_missing = (
            self._rules.missing_fields(active_code, self._state.draft.values)
            if active_code is not None
            else ()
        )
        context = None
        if active_code is not None:
            expected_field = (
                previous_missing[0] if previous_missing and not self._pending() else None
            )
            context = ExtractionTurnContext(active_code.value, expected_field)
        outcome = self._extractor.extract(message, context=context)
        if not outcome.succeeded:
            return self._technical_fallback(message, outcome.error_code or "provider_error")
        self._clear_technical_failures()
        if outcome.classification == "unsupported":
            return self._unsupported(message)
        if outcome.classification == "ambiguous" or outcome.procedure_code is None:
            if active_code is not None:
                if previous_missing and not self._pending():
                    field_id = previous_missing[0]
                    attempts = dict(self._state.clarification_attempts)
                    attempts[field_id] = attempts.get(field_id, 0) + 1
                    self._state = replace(self._state, clarification_attempts=attempts)
                prompt, action = self._resume_prompt(active_code)
                return self._reply_without_draft_change(
                    message,
                    f"Tôi chưa hiểu câu trả lời trong ngữ cảnh thủ tục hiện tại. {prompt}",
                    action,
                )
            return self._reply_without_draft_change(
                message,
                "Bạn cần hỗ trợ đăng ký tạm trú, xác nhận diện tích nhà ở để đăng ký "
                "thường trú hay cấp bản sao Giấy khai sinh?",
                NextAction.ASK_CLARIFICATION,
            )

        code = ProcedureCode(outcome.procedure_code)
        current_code = self._state.draft.procedure_code
        if current_code is not None and current_code is not code:
            return self._reply_without_draft_change(
                message,
                "Yêu cầu mới thuộc thủ tục khác. Hãy dùng /reset trước khi chuyển thủ tục.",
                NextAction.ASK_CLARIFICATION,
            )

        draft = self._state.draft
        if current_code is None:
            pack = self._repository.get_by_code(code)
            draft = replace(draft, procedure_code=code, pack_version=pack.version)

        suggestions = list(self._state.suggestions)
        valid_fields: dict[str, JSONValue] = {}
        for field_id, value in outcome.fields.items():
            if field_id in draft.confirmed_fields or field_id in draft.dirty_fields:
                continue
            try:
                self._validate_field_value(code, field_id, value)
            except ValueError:
                continue
            valid_fields[field_id] = value
            suggestions = [
                item
                for item in suggestions
                if not (item.field_id == field_id and item.status is SuggestionStatus.PENDING)
            ]
            suggestions.append(
                FieldSuggestion(
                    suggestion_id=f"{draft.revision}:{self._state.turn_number + 1}:{field_id}",
                    field_id=field_id,
                    current_value=draft.values.get(field_id),
                    suggested_value=value,
                    evidence=outcome.evidence.get(field_id, ""),
                    status=SuggestionStatus.PENDING,
                    revision=draft.revision,
                )
            )

        attempts = dict(self._state.clarification_attempts)
        if previous_missing and not valid_fields:
            field_id = previous_missing[0]
            attempts[field_id] = attempts.get(field_id, 0) + 1
        self._state = ConversationState(
            draft=draft,
            messages=self._state.messages,
            turn_number=self._state.turn_number,
            clarification_attempts=attempts,
            suggestions=tuple(suggestions),
            asked_question_ids=self._state.asked_question_ids,
        )
        pending = self._pending()
        if pending:
            reply = (
                f"Tôi đã tạo {len(pending)} đề xuất. "
                "Hãy Accept, Reject hoặc Edit từng đề xuất trước khi đi tiếp."
            )
            action = NextAction.CONFIRM_SUGGESTION
        else:
            reply, action = self._next_prompt(code)
        return self._finish_turn(message, reply, action, extracted_fields=valid_fields)

    def accept_suggestion(self, suggestion_id: str, *, expected_revision: int) -> TurnResult:
        return self._resolve_suggestion(
            suggestion_id,
            SuggestionStatus.ACCEPTED,
            expected_revision=expected_revision,
        )

    def reject_suggestion(self, suggestion_id: str, *, expected_revision: int) -> TurnResult:
        self._ensure_open()
        self._require_revision(expected_revision)
        suggestion = self._pending_by_id(suggestion_id)
        new_revision = self._state.draft.revision + 1
        attempts = dict(self._state.clarification_attempts)
        attempts[suggestion.field_id] = attempts.get(suggestion.field_id, 0) + 1
        self._state = replace(
            self._state,
            draft=replace(self._state.draft, revision=new_revision),
            suggestions=self._rebase_suggestions(
                new_revision,
                resolved_id=suggestion_id,
                resolved_status=SuggestionStatus.REJECTED,
            ),
            clarification_attempts=attempts,
        )
        return self._result_after_action(f"Đã bỏ đề xuất cho {suggestion.field_id}.")

    def edit_suggestion(
        self,
        suggestion_id: str,
        value: JSONValue,
        *,
        expected_revision: int,
    ) -> TurnResult:
        return self._resolve_suggestion(
            suggestion_id,
            SuggestionStatus.EDITED,
            expected_revision=expected_revision,
            edited_value=value,
        )

    def edit_field(
        self,
        field_id: str,
        value: JSONValue,
        *,
        expected_revision: int,
    ) -> TurnResult:
        """Apply a validated manual form edit as confirmed and user-owned data."""

        self._ensure_open()
        self._require_revision(expected_revision)
        draft = self._state.draft
        code = draft.procedure_code
        if code is None:
            raise ProcedureNotSelectedError("Select a procedure before editing its form")
        self._validate_field_value(code, field_id, value)

        values = dict(draft.values)
        values[field_id] = value
        confirmed = set(draft.confirmed_fields)
        confirmed.add(field_id)
        dirty = set(draft.dirty_fields)
        dirty.add(field_id)
        new_revision = draft.revision + 1
        new_draft = CaseDraft(
            procedure_code=code,
            values=values,
            confirmed_fields=frozenset(confirmed),
            dirty_fields=frozenset(dirty),
            revision=new_revision,
            pack_version=draft.pack_version,
        )
        attempts = dict(self._state.clarification_attempts)
        attempts.pop(field_id, None)
        self._state = replace(
            self._state,
            draft=new_draft,
            suggestions=self._rebase_suggestions(
                new_revision,
                superseded_field=field_id,
            ),
            clarification_attempts=attempts,
        )
        return self._result_after_action(f"Đã cập nhật {field_id} từ biểu mẫu.")

    def close(self) -> None:
        self._state = ConversationState()
        self._closed = True

    def _resolve_suggestion(
        self,
        suggestion_id: str,
        status: SuggestionStatus,
        *,
        expected_revision: int,
        edited_value: JSONValue = None,
    ) -> TurnResult:
        self._ensure_open()
        self._require_revision(expected_revision)
        suggestion = self._pending_by_id(suggestion_id)
        draft = self._state.draft
        if suggestion.revision != draft.revision:
            raise RevisionConflictError("Suggestion is stale for the current draft revision")
        code = draft.procedure_code
        if code is None:
            raise RuntimeError("Cannot apply a suggestion without a procedure")
        value = edited_value if status is SuggestionStatus.EDITED else suggestion.suggested_value
        self._validate_field_value(code, suggestion.field_id, value)

        values = dict(draft.values)
        values[suggestion.field_id] = value
        confirmed = set(draft.confirmed_fields)
        confirmed.add(suggestion.field_id)
        dirty = set(draft.dirty_fields)
        if status is SuggestionStatus.EDITED:
            dirty.add(suggestion.field_id)
        new_revision = draft.revision + 1
        new_draft = CaseDraft(
            procedure_code=code,
            values=values,
            confirmed_fields=frozenset(confirmed),
            dirty_fields=frozenset(dirty),
            revision=new_revision,
            pack_version=draft.pack_version,
        )
        self._state = replace(
            self._state,
            draft=new_draft,
            suggestions=self._rebase_suggestions(
                new_revision,
                resolved_id=suggestion_id,
                resolved_status=status,
            ),
        )
        verb = "Đã sửa và xác nhận" if status is SuggestionStatus.EDITED else "Đã chấp nhận"
        return self._result_after_action(f"{verb} {suggestion.field_id}.")

    def _result_after_action(self, prefix: str) -> TurnResult:
        code = self._state.draft.procedure_code
        if code is None:
            raise RuntimeError("Conversation has no active procedure")
        pending = self._pending()
        if pending:
            return self._build_result(
                f"{prefix} Còn {len(pending)} đề xuất cần xác nhận.",
                NextAction.CONFIRM_SUGGESTION,
            )
        reply, action = self._next_prompt(code)
        return self._build_result(f"{prefix} {reply}", action)

    def _next_prompt(self, code: ProcedureCode) -> tuple[str, NextAction]:
        missing = self._rules.missing_fields(code, self._state.draft.values)
        if missing:
            field_id = missing[0]
            attempts = self._state.clarification_attempts.get(field_id, 0)
            question_id = self._question_id(code, field_id)
            if attempts >= 2 or question_id in self._state.asked_question_ids:
                return (
                    f"Hãy nhập trực tiếp trường {field_id} trên biểu mẫu.",
                    NextAction.MANUAL_INPUT,
                )
            self._state = replace(
                self._state,
                asked_question_ids=self._state.asked_question_ids + (question_id,),
            )
            return self._questions.question_for(code, field_id), NextAction.ASK_CLARIFICATION

        validation = self._rules.validate(code, self._state.draft.values)
        if validation.status is ValidationStatus.NEEDS_CORRECTION:
            return "Hồ sơ còn lỗi cần sửa trước khi tiếp tục.", NextAction.REQUEST_CORRECTION
        if validation.status is ValidationStatus.NEEDS_OFFICIAL_REVIEW:
            return (
                "Hồ sơ cần cơ quan có thẩm quyền kiểm tra thêm.",
                NextAction.REQUEST_OFFICIAL_REVIEW,
            )
        if validation.status is ValidationStatus.OUT_OF_SCOPE:
            return "Yêu cầu nằm ngoài phạm vi MVP.", NextAction.OUT_OF_SCOPE
        return "Thông tin đã sẵn sàng để bạn kiểm tra lần cuối.", NextAction.COMPLETE

    def _resume_prompt(self, code: ProcedureCode) -> tuple[str, NextAction]:
        pending = self._pending()
        if pending:
            return (
                f"Bạn còn {len(pending)} đề xuất cần Accept, Reject hoặc Edit trước khi đi tiếp.",
                NextAction.CONFIRM_SUGGESTION,
            )
        return self._next_prompt(code)

    def _finish_turn(
        self,
        user_message: str,
        reply: str,
        action: NextAction,
        *,
        extracted_fields: Mapping[str, JSONValue] | None = None,
    ) -> TurnResult:
        messages = self._state.messages + (
            ChatMessage(MessageRole.USER, user_message),
            ChatMessage(MessageRole.ASSISTANT, reply),
        )
        self._state = replace(
            self._state,
            messages=messages,
            turn_number=self._state.turn_number + 1,
        )
        return self._build_result(reply, action, extracted_fields=extracted_fields)

    def _build_result(
        self,
        reply: str,
        action: NextAction,
        *,
        extracted_fields: Mapping[str, JSONValue] | None = None,
    ) -> TurnResult:
        code = self._state.draft.procedure_code
        validation: ValidationResult | None = None
        missing: tuple[str, ...] = ()
        source_ids: tuple[str, ...] = ()
        if code is not None:
            validation = self._rules.validate(code, self._state.draft.values)
            missing = self._rules.missing_fields(code, self._state.draft.values)
            source_ids = self._repository.get_by_code(code).source_ids
        return TurnResult(
            reply=reply,
            state=self._state,
            next_action=action,
            source_ids=source_ids,
            missing_fields=missing,
            validation=validation,
            extracted_fields={} if extracted_fields is None else extracted_fields,
        )

    def _technical_fallback(self, message: str, error_code: str) -> TurnResult:
        key = "__extractor__"
        attempts = dict(self._state.clarification_attempts)
        attempts[key] = attempts.get(key, 0) + 1
        self._state = replace(self._state, clarification_attempts=attempts)
        action = NextAction.MANUAL_INPUT if attempts[key] >= 2 else NextAction.RETRY
        reply = (
            "Tôi chưa đọc được thông tin. Hãy nhập trực tiếp trên biểu mẫu."
            if action is NextAction.MANUAL_INPUT
            else "Tôi chưa đọc được thông tin; vui lòng thử diễn đạt lại."
        )
        return self._finish_turn(message, reply, action)

    def _clear_technical_failures(self) -> None:
        if "__extractor__" not in self._state.clarification_attempts:
            return
        attempts = dict(self._state.clarification_attempts)
        attempts.pop("__extractor__", None)
        self._state = replace(self._state, clarification_attempts=attempts)

    def _unsupported(self, message: str) -> TurnResult:
        active_code = self._state.draft.procedure_code
        if active_code is not None:
            prompt, _action = self._resume_prompt(active_code)
            return self._reply_without_draft_change(
                message,
                "Yêu cầu vừa rồi nằm ngoài ba thủ tục được hỗ trợ trong MVP. "
                f"Phiên thủ tục hiện tại vẫn được giữ nguyên. {prompt}",
                NextAction.OUT_OF_SCOPE,
            )
        return self._reply_without_draft_change(
            message,
            "Yêu cầu này nằm ngoài ba thủ tục được hỗ trợ trong MVP.",
            NextAction.OUT_OF_SCOPE,
        )

    def _reply_without_draft_change(
        self, message: str, reply: str, action: NextAction
    ) -> TurnResult:
        return self._finish_turn(message, reply, action)

    def _pending(self) -> tuple[FieldSuggestion, ...]:
        return tuple(
            item for item in self._state.suggestions if item.status is SuggestionStatus.PENDING
        )

    def _pending_by_id(self, suggestion_id: str) -> FieldSuggestion:
        for item in self._pending():
            if item.suggestion_id == suggestion_id:
                return item
        raise ValueError("Unknown or already resolved suggestion")

    def _rebase_suggestions(
        self,
        new_revision: int,
        *,
        resolved_id: str | None = None,
        resolved_status: SuggestionStatus | None = None,
        superseded_field: str | None = None,
    ) -> tuple[FieldSuggestion, ...]:
        if (resolved_id is None) is not (resolved_status is None):
            raise AssertionError("resolved suggestion ID and status must be provided together")
        updated: list[FieldSuggestion] = []
        for item in self._state.suggestions:
            if item.suggestion_id == resolved_id:
                assert resolved_status is not None
                updated.append(replace(item, status=resolved_status))
            elif (
                item.status is SuggestionStatus.PENDING
                and superseded_field is not None
                and item.field_id == superseded_field
            ):
                updated.append(replace(item, status=SuggestionStatus.REJECTED))
            elif item.status is SuggestionStatus.PENDING:
                suffix = item.suggestion_id.split(":", 1)[-1]
                updated.append(
                    replace(
                        item,
                        suggestion_id=f"{new_revision}:{suffix}",
                        revision=new_revision,
                    )
                )
            else:
                updated.append(item)
        return tuple(updated)

    def _require_revision(self, expected_revision: int) -> None:
        if self._state.draft.revision != expected_revision:
            raise RevisionConflictError("Draft revision does not match expected_revision")

    def _validate_field_value(
        self,
        code: ProcedureCode,
        field_id: str,
        value: JSONValue,
    ) -> None:
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"{field_id} must not be blank")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{field_id} must be a finite number")
        self._rules.validate_field_value(code, field_id, value)

    @staticmethod
    def _question_id(code: ProcedureCode, field_id: str) -> str:
        return f"{code.value}:{field_id}"

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Conversation session is closed")


def build_session(
    extractor: StructuredExtractor | Extractor, repository: ProcedureRepository
) -> ConversationSession:
    return ConversationSession(extractor, repository)
