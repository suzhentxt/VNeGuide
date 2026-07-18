"""Suggestion-aware conversation session independent of terminal I/O."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import replace
from typing import Protocol

from vneguide.ai import (
    MAX_RESPONDER_HISTORY_TURNS,
    ExtractionOutcome,
    ExtractionTurnContext,
    GroundedReply,
    InformationRequest,
    MemoryCompactor,
    ResponderContext,
    StructuredExtractor,
)
from vneguide.data import ProcedureRepository
from vneguide.domain import (
    CaseDraft,
    ChatMessage,
    ConversationState,
    FieldSuggestion,
    FieldType,
    JSONValue,
    MessageRole,
    NextAction,
    ProcedureCode,
    SuggestionStatus,
    TurnResult,
    ValidationResult,
    ValidationStatus,
)
from vneguide.memory import LongTermMemory, MemoryScope
from vneguide.rules import ProcedureQAResponder, QuestionSelector, RuleEngine

_AFFIRMATIVE_CONFIRMATIONS = frozenset(
    {
        "chính xác",
        "dạ",
        "dạ đúng",
        "dạ đúng ạ",
        "dạ đúng rồi",
        "dạ đúng rồi ạ",
        "dạ vâng",
        "đúng",
        "đúng rồi",
        "đúng vậy",
        "ok",
        "okay",
        "phải",
        "phải rồi",
        "vâng",
        "vâng ạ",
        "vâng đúng rồi",
    }
)
_NEGATIVE_CONFIRMATIONS = frozenset(
    {
        "không",
        "không ạ",
        "không đúng",
        "không phải",
        "không phải ạ",
        "sai",
        "sai rồi",
    }
)
_SAFE_NLG_ACKNOWLEDGEMENTS = frozenset(
    {
        "Dạ, em đã hiểu yêu cầu của anh/chị ạ.",
        "Dạ, em đã ghi nhận thông tin anh/chị vừa cung cấp ạ.",
        "Dạ, em hiểu rồi ạ.",
    }
)
_COMPACTION_THRESHOLD_MESSAGES = MAX_RESPONDER_HISTORY_TURNS * 2


class Extractor(Protocol):
    def extract(
        self,
        message: str,
        *,
        context: ExtractionTurnContext | None = None,
    ) -> ExtractionOutcome: ...


class Responder(Protocol):
    def respond(self, context: ResponderContext) -> object: ...


class RevisionConflictError(ValueError):
    """A client mutation targets an older draft revision."""


class ProcedureNotSelectedError(ValueError):
    """A form mutation cannot be validated before selecting a procedure."""


class ProcedureConflictError(ValueError):
    """A requested procedure conflicts with the active session procedure."""


class ConversationSession:
    """Own one ephemeral conversation and its confirmed draft."""

    def __init__(
        self,
        extractor: Extractor,
        repository: ProcedureRepository,
        *,
        responder: Responder | None = None,
        compactor: MemoryCompactor | None = None,
        long_term_memory: LongTermMemory | None = None,
    ) -> None:
        self._extractor = extractor
        self._repository = repository
        self._rules = RuleEngine(repository)
        self._questions = QuestionSelector(repository)
        self._qa = ProcedureQAResponder(repository)
        self._responder = responder
        self._compactor = compactor
        self._long_term_memory = long_term_memory
        self._memory_scope: MemoryScope | None = None
        self._state = ConversationState()
        self._closed = False

    @property
    def state(self) -> ConversationState:
        return self._state

    def bind_memory_scope(self, *, user_id: str, run_id: str) -> None:
        """Bind opaque Mem0 identifiers once, before the first turn."""

        self._ensure_open()
        scope = MemoryScope(user_id=user_id, run_id=run_id)
        if self._state.turn_number or self._memory_scope is not None:
            raise RuntimeError("Memory scope must be bound exactly once before the first turn")
        self._memory_scope = scope

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
        pending_code = self._state.pending_procedure_code
        rejects_pending = pending_code is not None and _rejects_pending_procedure(message)
        confirmation = _confirmation_value(message) if pending_code is not None else None
        if confirmation is True:
            return self._confirm_pending_procedure(message)
        if confirmation is False:
            return self._reject_pending_procedure(message)

        previous_missing = (
            self._rules.missing_fields(active_code, self._state.draft.values)
            if active_code is not None
            else ()
        )
        context = None
        recent_topics = self._state.recent_information_topics
        recent_code = self._state.recent_information_procedure_code
        recent_code_value = None if recent_code is None else recent_code.value
        if active_code is not None:
            expected_field = (
                previous_missing[0] if previous_missing and not self._pending() else None
            )
            context = ExtractionTurnContext(
                active_code.value,
                expected_field,
                recent_information_topics=recent_topics,
                recent_information_procedure_code=recent_code_value,
            )
        elif pending_code is not None:
            context = ExtractionTurnContext(
                pending_code.value,
                confirmation_required=True,
                recent_information_topics=recent_topics,
                recent_information_procedure_code=recent_code_value,
            )
        outcome = self._extractor.extract(message, context=context)
        if not outcome.succeeded:
            if rejects_pending:
                return self._reject_pending_procedure(message)
            return self._technical_fallback(
                message,
                outcome.error_code or "provider_error",
                invalid_field_id=outcome.invalid_field_id,
            )
        self._clear_technical_failures()
        if outcome.classification == "informational":
            return self._informational(message, outcome)
        if pending_code is not None and rejects_pending:
            selects_different_procedure = (
                outcome.classification == "supported"
                and outcome.procedure_code is not None
                and ProcedureCode(outcome.procedure_code) != pending_code
            )
            if not selects_different_procedure:
                return self._reject_pending_procedure(message)
        if outcome.classification == "unsupported":
            return self._unsupported(message)
        if outcome.classification == "ambiguous" or outcome.procedure_code is None:
            if pending_code is not None:
                return self._reply_without_draft_change(
                    message,
                    self._confirmation_prompt(pending_code, heard_clearly=False),
                    NextAction.CONFIRM_PROCEDURE,
                )
            if active_code is not None:
                if previous_missing and not self._pending():
                    field_id = previous_missing[0]
                    attempts = dict(self._state.clarification_attempts)
                    attempts[field_id] = attempts.get(field_id, 0) + 1
                    self._state = replace(self._state, clarification_attempts=attempts)
                prompt, action = self._resume_prompt(active_code)
                return self._reply_without_draft_change(
                    message,
                    f"Dạ, em chưa hiểu rõ câu trả lời vừa rồi. {prompt}",
                    action,
                )
            return self._reply_without_draft_change(
                message,
                self._procedure_choice_prompt(),
                NextAction.ASK_CLARIFICATION,
            )

        if outcome.classification == "supported" and self._state.recent_information_topics:
            self._state = replace(
                self._state,
                recent_information_procedure_code=None,
                recent_information_topics=(),
            )
        code = ProcedureCode(outcome.procedure_code)
        current_code = self._state.draft.procedure_code
        pending_code = self._state.pending_procedure_code
        if current_code is None:
            if pending_code is None or pending_code != code:
                self._state = replace(self._state, pending_procedure_code=code)
                return self._finish_turn(
                    message,
                    self._confirmation_prompt(code),
                    NextAction.CONFIRM_PROCEDURE,
                )
            self._activate_pending_procedure(code)
            current_code = code

        if current_code is not None and current_code is not code:
            return self._reply_without_draft_change(
                message,
                "Dạ, yêu cầu mới thuộc thủ tục khác. Anh/chị vui lòng đặt lại phiên trước khi "
                "chuyển thủ tục ạ.",
                NextAction.ASK_CLARIFICATION,
            )

        draft = self._state.draft
        correction = _is_field_correction(message)

        suggestions = list(self._state.suggestions)
        valid_fields: dict[str, JSONValue] = {}
        for field_id, value in outcome.fields.items():
            if field_id in draft.dirty_fields:
                continue
            if field_id in draft.confirmed_fields and not correction:
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
        self._state = replace(
            self._state,
            clarification_attempts=attempts,
            suggestions=tuple(suggestions),
        )
        pending = self._pending()
        if pending:
            if len(pending) == 1:
                label = self._field_label(code, pending[0].field_id)
                if correction:
                    reply = (
                        f"Tôi đã ghi nhận nội dung sửa cho mục {label}. "
                        "Bước tiếp theo: anh/chị kiểm tra đề xuất giúp tôi."
                    )
                else:
                    reply = (
                        f"Tôi đã ghi nhận mục {label}. "
                        "Bước tiếp theo: anh/chị kiểm tra đề xuất giúp tôi."
                    )
            else:
                reply = (
                    f"Em đã điền sẵn {len(pending)} mục. Anh/chị kiểm tra từng đề xuất rồi "
                    "chọn Đồng ý, Bỏ qua hoặc Sửa giúp em ạ."
                )
            action = NextAction.CONFIRM_SUGGESTION
        else:
            reply, action = self._next_prompt(code)
        reply = self._with_safe_nlg_acknowledgement(outcome.reply, reply)
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
        code = self._state.draft.procedure_code
        assert code is not None
        label = self._field_label(code, suggestion.field_id)
        return self._result_after_action(f"Dạ, em đã bỏ đề xuất cho mục {label}.")

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
        user_message: str | None = None,
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
        label = self._field_label(code, field_id)
        prefix = f"Dạ, em đã cập nhật mục {label} từ biểu mẫu."
        if user_message is None:
            return self._result_after_action(prefix)
        reply, action = self._reply_after_action(prefix)
        return self._finish_turn(user_message, reply, action)

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
        label = self._field_label(code, suggestion.field_id)
        verb = "đã sửa và xác nhận" if status is SuggestionStatus.EDITED else "đã chấp nhận"
        return self._result_after_action(f"Dạ, em {verb} mục {label}.")

    def _result_after_action(self, prefix: str) -> TurnResult:
        reply, action = self._reply_after_action(prefix)
        return self._finish_action(reply, action)

    def _reply_after_action(self, prefix: str) -> tuple[str, NextAction]:
        code = self._state.draft.procedure_code
        if code is None:
            raise RuntimeError("Conversation has no active procedure")
        pending = self._pending()
        if pending:
            return (
                f"{prefix} Anh/chị còn {len(pending)} đề xuất cần kiểm tra ạ.",
                NextAction.CONFIRM_SUGGESTION,
            )
        reply, action = self._next_prompt(code)
        return f"{prefix} {reply}", action

    def _next_prompt(
        self,
        code: ProcedureCode,
        *,
        record_question: bool = True,
    ) -> tuple[str, NextAction]:
        missing = self._rules.missing_fields(code, self._state.draft.values)
        if missing:
            field_id = missing[0]
            attempts = self._state.clarification_attempts.get(field_id, 0)
            question_id = self._question_id(code, field_id)
            if attempts >= 2:
                label = self._field_label(code, field_id)
                return (
                    f"Tôi chưa ghi nhận được mục {label}. Bạn có thể nhập trực tiếp vào biểu mẫu.",
                    NextAction.MANUAL_INPUT,
                )
            if record_question and question_id not in self._state.asked_question_ids:
                self._state = replace(
                    self._state,
                    asked_question_ids=self._state.asked_question_ids + (question_id,),
                )
            return self._questions.question_for(code, field_id), NextAction.ASK_CLARIFICATION

        validation = self._rules.validate(code, self._state.draft.values)
        if validation.status is ValidationStatus.NEEDS_CORRECTION:
            return (
                "Hồ sơ còn một số mục cần sửa. Anh/chị xem phần báo lỗi trên biểu mẫu giúp em ạ.",
                NextAction.REQUEST_CORRECTION,
            )
        if validation.status is ValidationStatus.NEEDS_OFFICIAL_REVIEW:
            return (
                "Thông tin này cần cơ quan có thẩm quyền kiểm tra thêm, anh/chị nhé.",
                NextAction.REQUEST_OFFICIAL_REVIEW,
            )
        if validation.status is ValidationStatus.OUT_OF_SCOPE:
            return "Yêu cầu này nằm ngoài phạm vi VNeGuide đang hỗ trợ ạ.", NextAction.OUT_OF_SCOPE
        return (
            "Em đã gom đủ thông tin. Anh/chị kiểm tra lại một lượt trước khi nộp nhé ạ.",
            NextAction.COMPLETE,
        )

    def _resume_prompt(
        self,
        code: ProcedureCode,
        *,
        record_question: bool = True,
    ) -> tuple[str, NextAction]:
        pending = self._pending()
        if pending:
            return (
                f"Anh/chị còn {len(pending)} đề xuất cần chọn Đồng ý, Bỏ qua hoặc Sửa trước "
                "khi đi tiếp ạ.",
                NextAction.CONFIRM_SUGGESTION,
            )
        return self._next_prompt(code, record_question=record_question)

    def _finish_turn(
        self,
        user_message: str,
        reply: str,
        action: NextAction,
        *,
        extracted_fields: Mapping[str, JSONValue] | None = None,
        source_ids: tuple[str, ...] | None = None,
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
        self._maybe_compact()
        if self._long_term_memory is not None and self._memory_scope is not None:
            self._long_term_memory.remember(self._memory_scope, user_message)
        return self._build_result(
            reply,
            action,
            extracted_fields=extracted_fields,
            source_ids=source_ids,
        )

    def _finish_action(self, reply: str, action: NextAction) -> TurnResult:
        """Record the assistant response generated by a form/suggestion mutation."""

        self._state = replace(
            self._state,
            messages=self._state.messages + (ChatMessage(MessageRole.ASSISTANT, reply),),
        )
        self._maybe_compact()
        return self._build_result(reply, action)

    def _maybe_compact(self) -> None:
        """Fold old messages into ``memory_summary`` once the log exceeds its window.

        Compaction is best-effort: on any compactor failure the messages are
        left untouched and retried on a later turn, so a memory hiccup never
        blocks the citizen's reply.
        """

        if self._compactor is None:
            return
        messages = self._state.messages
        if len(messages) <= _COMPACTION_THRESHOLD_MESSAGES:
            return
        keep = messages[-MAX_RESPONDER_HISTORY_TURNS:]
        old = messages[:-MAX_RESPONDER_HISTORY_TURNS]
        result = self._compactor.compact(self._state.memory_summary, old)
        if not result.succeeded or result.summary is None:
            return
        self._state = replace(
            self._state,
            messages=keep,
            memory_summary=result.summary,
        )

    def _build_result(
        self,
        reply: str,
        action: NextAction,
        *,
        extracted_fields: Mapping[str, JSONValue] | None = None,
        source_ids: tuple[str, ...] | None = None,
    ) -> TurnResult:
        code = self._state.draft.procedure_code
        validation: ValidationResult | None = None
        missing: tuple[str, ...] = ()
        resolved_source_ids: tuple[str, ...] = ()
        if code is not None:
            validation = self._rules.validate(code, self._state.draft.values)
            missing = self._rules.missing_fields(code, self._state.draft.values)
            if missing and validation.status is ValidationStatus.READY_TO_SUBMIT:
                validation = replace(
                    validation,
                    status=ValidationStatus.NEEDS_CORRECTION,
                    readiness_score=None,
                )
            resolved_source_ids = self._repository.get_by_code(code).source_ids
        if source_ids is not None:
            resolved_source_ids = tuple(dict.fromkeys(source_ids))
        return TurnResult(
            reply=reply,
            state=self._state,
            next_action=action,
            source_ids=resolved_source_ids,
            missing_fields=missing,
            validation=validation,
            extracted_fields={} if extracted_fields is None else extracted_fields,
        )

    def _informational(
        self,
        message: str,
        outcome: ExtractionOutcome,
    ) -> TurnResult:
        """Answer a reviewed FAQ without mutating form workflow state."""

        request = outcome.information_request
        if request is None:
            return self._finish_turn(
                message,
                "Dạ, để trả lời đúng nguồn, em cần biết anh/chị đang hỏi về thủ tục nào. "
                + self._procedure_choice_prompt(),
                NextAction.ASK_CLARIFICATION,
            )
        resolved_code = outcome.procedure_code
        if resolved_code is None:
            known_code = (
                self._state.draft.procedure_code
                or self._state.pending_procedure_code
                or self._state.recent_information_procedure_code
            )
            resolved_code = None if known_code is None else known_code.value
        if resolved_code is None:
            return self._finish_turn(
                message,
                "Dạ, để trả lời đúng nguồn, em cần biết anh/chị đang hỏi về thủ tục nào. "
                + self._procedure_choice_prompt(),
                NextAction.ASK_CLARIFICATION,
            )
        try:
            code = ProcedureCode(resolved_code)
        except ValueError:
            return self._finish_turn(
                message,
                self._procedure_choice_prompt(),
                NextAction.ASK_CLARIFICATION,
            )

        active_code = self._state.draft.procedure_code
        pending_code = self._state.pending_procedure_code
        draft_values = self._state.draft.values if active_code is code else {}
        answer = self._qa.answer(code, request, draft_values=draft_values)
        self._state = replace(
            self._state,
            recent_information_procedure_code=code,
            recent_information_topics=request.topics,
        )

        grounded = self._try_respond(
            message,
            classification="informational",
            procedure_code=code.value,
            information_request=request,
            draft_values=draft_values,
        )
        reply_text = answer.text
        reply_sources = answer.source_ids
        if grounded is not None:
            reply_text, _off_domain, reply_sources = grounded

        if active_code is None:
            if pending_code is not code:
                self._state = replace(self._state, pending_procedure_code=code)
            return self._finish_turn(
                message,
                f"{reply_text}\n\n{self._confirmation_prompt(code)}",
                NextAction.CONFIRM_PROCEDURE,
                source_ids=reply_sources,
            )

        _prompt, action = self._resume_prompt(active_code, record_question=False)
        bridge = self._action_bridge(action)
        if active_code is code:
            reply = f"{reply_text}\n\n{bridge}"
        else:
            current_name = self._questions.procedure_label(active_code)
            reply = (
                f"{reply_text}\n\nThông tin trên chỉ để tham khảo. Phiên hiện tại vẫn đang "
                f"hỗ trợ thủ tục {current_name}; nếu muốn chuyển thủ tục, anh/chị cần đặt lại "
                f"phiên trước ạ. {bridge}"
            )
        return self._finish_turn(
            message,
            reply,
            action,
            source_ids=reply_sources,
        )

    def _technical_fallback(
        self,
        message: str,
        error_code: str,
        *,
        invalid_field_id: str | None = None,
    ) -> TurnResult:
        key = "__extractor__"
        attempts = dict(self._state.clarification_attempts)
        attempts[key] = attempts.get(key, 0) + 1
        self._state = replace(self._state, clarification_attempts=attempts)
        pending_code = self._state.pending_procedure_code
        if pending_code is not None:
            return self._finish_turn(
                message,
                self._confirmation_prompt(pending_code, heard_clearly=False),
                NextAction.CONFIRM_PROCEDURE,
            )
        use_manual_input = attempts[key] >= 2
        action = NextAction.FILL_MISSING_FIELD
        if error_code == "invalid_value" and invalid_field_id is not None:
            reply = self._invalid_value_reply(invalid_field_id)
            return self._finish_turn(message, reply, action)
        reply = (
            "Dạ, em chưa đọc được thông tin. Anh/chị nhập trực tiếp trên biểu mẫu giúp em ạ."
            if use_manual_input
            else "Dạ, em chưa nghe rõ. Anh/chị nói lại theo cách khác giúp em được không ạ?"
        )
        return self._finish_turn(message, reply, action)

    def _invalid_value_reply(self, field_id: str) -> str:
        active_code = self._state.draft.procedure_code
        label = self._field_label(active_code, field_id) if active_code is not None else field_id
        hint = self._field_format_hint(active_code, field_id) if active_code is not None else ""
        lead = f"Dạ, mục {label} chưa đúng định dạng."
        if hint:
            return f"{lead} {hint} Anh/chị kiểm tra rồi nói lại giúp em ạ."
        return f"{lead} Anh/chị kiểm tra rồi nói lại giúp em ạ."

    def _field_format_hint(self, code: ProcedureCode, field_id: str) -> str:
        for field in self._repository.fields_for(code):
            if field.field_id != field_id:
                continue
            if field.help_text:
                return field.help_text.rstrip(".") + "."
            if field.field_type is FieldType.DATE:
                return "Anh/chị nhập đầy đủ ngày/tháng/năm (ví dụ 01/01/1990) ạ."
            if field.field_type is FieldType.INTEGER:
                return "Anh/chị nhập một số nguyên ạ."
            if field.field_type is FieldType.NUMBER:
                return "Anh/chị nhập một số ạ."
            if field.field_type is FieldType.BOOLEAN:
                return 'Anh/chị trả lời "Có" hoặc "Không" ạ.'
            if field.field_type is FieldType.ENUM:
                return "Anh/chị chọn một trong các lựa chọn đã liệt kê ạ."
            return ""
        return ""

    def _clear_technical_failures(self) -> None:
        if "__extractor__" not in self._state.clarification_attempts:
            return
        attempts = dict(self._state.clarification_attempts)
        attempts.pop("__extractor__", None)
        self._state = replace(self._state, clarification_attempts=attempts)

    def _unsupported(self, message: str) -> TurnResult:
        active_code = self._state.draft.procedure_code
        pending_code = self._state.pending_procedure_code
        if pending_code is not None:
            return self._reply_without_draft_change(
                message,
                "Dạ, nội dung vừa rồi nằm ngoài ba thủ tục em đang hỗ trợ. "
                + self._confirmation_prompt(pending_code),
                NextAction.CONFIRM_PROCEDURE,
            )
        if active_code is not None:
            return self._reply_without_draft_change(
                message,
                "Dạ, nội dung vừa rồi nằm ngoài ba thủ tục em đang hỗ trợ. "
                "Phiên hiện tại vẫn được giữ nguyên; anh/chị có thể tiếp tục mục đang điền ạ.",
                NextAction.OUT_OF_SCOPE,
            )
        grounded = self._try_respond(message, classification="unsupported")
        if grounded is not None:
            reply, off_domain, source_ids = grounded
            action = NextAction.OUT_OF_SCOPE if off_domain else NextAction.PRESENT_GUIDANCE
            return self._finish_turn(
                message,
                reply,
                action,
                source_ids=source_ids or None,
            )
        return self._reply_without_draft_change(
            message,
            "Dạ, nội dung này nằm ngoài ba thủ tục VNeGuide đang hỗ trợ ạ.",
            NextAction.OUT_OF_SCOPE,
        )

    def _try_respond(
        self,
        message: str,
        *,
        classification: str,
        procedure_code: str | None = None,
        information_request: InformationRequest | None = None,
        draft_values: Mapping[str, JSONValue] | None = None,
    ) -> tuple[str, bool, tuple[str, ...]] | None:
        """Generate a grounded reply, or ``None`` to fall back deterministically."""

        if self._responder is None:
            return None
        active_code = self._state.draft.procedure_code
        pending_code = self._state.pending_procedure_code
        filled_labels, missing_labels = self._form_labels(active_code)
        recent_turns = self._state.messages[-MAX_RESPONDER_HISTORY_TURNS:]
        long_term_memories: tuple[str, ...] = ()
        if self._long_term_memory is not None and self._memory_scope is not None:
            long_term_memories = self._long_term_memory.recall(self._memory_scope)
        try:
            context = ResponderContext(
                user_message=message,
                classification=classification,
                procedure_code=procedure_code,
                information_request=information_request,
                active_procedure_code=None if active_code is None else active_code.value,
                pending_procedure_code=None if pending_code is None else pending_code.value,
                filled_field_labels=filled_labels,
                missing_field_labels=missing_labels,
                draft_values={} if draft_values is None else draft_values,
                recent_turns=recent_turns,
                memory_summary=self._state.memory_summary,
                long_term_memories=long_term_memories,
            )
        except ValueError:
            return None
        result = self._responder.respond(context)
        if not isinstance(result, GroundedReply) or not result.succeeded or not result.text:
            return None
        return result.text, result.off_domain, result.source_ids

    def _form_labels(
        self, active_code: ProcedureCode | None
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        if active_code is None:
            return (), ()
        values = self._state.draft.values
        filled = tuple(
            self._field_label(active_code, field_id)
            for field_id, value in values.items()
            if value not in (None, "", [])
        )
        missing_ids = self._rules.missing_fields(active_code, values)
        missing = tuple(self._field_label(active_code, field_id) for field_id in missing_ids)
        return filled, missing

    def _confirm_pending_procedure(self, message: str) -> TurnResult:
        code = self._state.pending_procedure_code
        if code is None:
            raise RuntimeError("Conversation has no pending procedure")
        self._clear_technical_failures()
        self._activate_pending_procedure(code)
        prompt, action = self._next_prompt(code)
        procedure_name = self._questions.procedure_label(code)
        return self._finish_turn(
            message,
            f"Tôi đã ghi nhận anh/chị muốn {procedure_name}. Bước tiếp theo: {prompt}",
            action,
        )

    @staticmethod
    def _action_bridge(action: NextAction) -> str:
        if action is NextAction.CONFIRM_SUGGESTION:
            return "Bước tiếp theo: kiểm tra đề xuất đang chờ."
        if action is NextAction.REQUEST_CORRECTION:
            return "Bước tiếp theo: sửa các mục đang được báo lỗi."
        if action is NextAction.REQUEST_OFFICIAL_REVIEW:
            return "Bước tiếp theo: nhờ cơ quan có thẩm quyền kiểm tra."
        if action is NextAction.COMPLETE:
            return "Bước tiếp theo: kiểm tra lại hồ sơ trước khi tiếp tục."
        if action is NextAction.OUT_OF_SCOPE:
            return "Phiên hiện tại vẫn được giữ nguyên."
        return "Bước tiếp theo: tiếp tục mục đang điền."

    def _reject_pending_procedure(self, message: str) -> TurnResult:
        self._state = replace(
            self._state,
            pending_procedure_code=None,
            recent_information_procedure_code=None,
            recent_information_topics=(),
        )
        self._clear_technical_failures()
        return self._finish_turn(
            message,
            "Dạ, em đã bỏ lựa chọn vừa rồi. " + self._procedure_choice_prompt(),
            NextAction.ASK_CLARIFICATION,
        )

    def _activate_pending_procedure(self, code: ProcedureCode) -> None:
        if self._state.pending_procedure_code is not code:
            raise RuntimeError("Pending procedure does not match the procedure being activated")
        pack = self._repository.get_by_code(code)
        self._state = replace(
            self._state,
            pending_procedure_code=None,
            draft=replace(
                self._state.draft,
                procedure_code=code,
                pack_version=pack.version,
            ),
        )

    def _confirmation_prompt(
        self,
        code: ProcedureCode,
        *,
        heard_clearly: bool = True,
    ) -> str:
        procedure_name = self._questions.procedure_label(code)
        if heard_clearly:
            lead = f"Dạ, em hiểu anh/chị muốn làm thủ tục {procedure_name}."
        else:
            lead = "Dạ, em chưa nghe rõ câu trả lời vừa rồi."
        return f'{lead} Đúng vậy không ạ? Anh/chị trả lời "Đúng" hoặc "Không phải" giúp em.'

    @staticmethod
    def _procedure_choice_prompt() -> str:
        return (
            "Anh/chị cần hỗ trợ đăng ký tạm trú, xác nhận diện tích nhà ở để đăng ký "
            "thường trú hay cấp bản sao Giấy khai sinh ạ?"
        )

    def _field_label(self, code: ProcedureCode, field_id: str) -> str:
        for field in self._repository.fields_for(code):
            if field.field_id == field_id:
                return field.label
        return field_id

    @staticmethod
    def _with_safe_nlg_acknowledgement(reply: str | None, deterministic: str) -> str:
        if reply is None:
            return deterministic
        compact = " ".join(reply.split())
        if compact not in _SAFE_NLG_ACKNOWLEDGEMENTS:
            return deterministic
        return f"{compact} {deterministic}"

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


def _confirmation_value(message: str) -> bool | None:
    phrase = _normalise_confirmation_phrase(message)
    if phrase in _AFFIRMATIVE_CONFIRMATIONS:
        return True
    if phrase in _NEGATIVE_CONFIRMATIONS:
        return False
    return None


def _is_field_correction(message: str) -> bool:
    """Return whether the citizen explicitly corrects previously confirmed data.

    Correction language is intentionally narrow.  A normal repeated value must
    not reopen confirmed state, while phrases such as ``địa chỉ đúng là`` or
    ``đổi thành`` may create a reviewable suggestion.  Dirty form fields remain
    protected by the caller regardless of this result.
    """

    phrase = _normalise_confirmation_phrase(message)
    patterns = (
        r"\bkhông\b.{0,80}\b(?:đúng|chính xác|phải) là\b",
        r"\b(?:địa chỉ|họ tên|tên|ngày sinh|số|thông tin) "
        r"(?:đúng|chính xác|mới) là\b",
        r"\b(?:xin|muốn|cần) (?:sửa|đính chính|cập nhật)\b",
        (
            r"\b(?:sửa|đính chính|cập nhật) (?:lại )?"
            r"(?:mục|thông tin|địa chỉ|họ tên|tên|ngày sinh|số)\b"
        ),
        r"\bđổi (?:lại )?(?:thành|từ)\b",
    )
    return any(re.search(pattern, phrase) for pattern in patterns)


def _normalise_confirmation_phrase(message: str) -> str:
    normalised = unicodedata.normalize("NFC", message).casefold()
    return " ".join(re.findall(r"\w+", normalised, flags=re.UNICODE))


def _rejects_pending_procedure(message: str) -> bool:
    normalised = unicodedata.normalize("NFC", message).casefold()
    phrase = _normalise_confirmation_phrase(message)
    procedure_rejections = (
        r"\bkhông phải (?:thủ tục|lựa chọn) (?:này|đó)\b",
        r"\b(?:không|chẳng|chả) muốn (?:làm|thực hiện) (?:thủ tục|lựa chọn) (?:này|đó)\b",
        r"\b(?:thủ tục|lựa chọn) (?:này|đó) (?:không đúng|sai)\b",
    )
    if any(re.search(pattern, phrase) for pattern in procedure_rejections):
        return True
    if phrase in {
        "thủ tục khác",
        "lựa chọn khác",
        "tôi muốn thủ tục khác",
        "tôi chọn thủ tục khác",
        "đổi sang thủ tục khác",
        "chuyển sang thủ tục khác",
        "không đúng thủ tục",
        "sai thủ tục",
        "sai thủ tục rồi",
        "nhầm thủ tục",
        "nhầm thủ tục rồi",
        "không đúng lựa chọn",
        "sai lựa chọn",
        "nhầm lựa chọn",
    }:
        return True
    return (
        re.match(
            r"^\s*(?:(?:dạ|vâng)\s*)?không\s*(?:ạ\s*)?[,.;:!?…-]",
            normalised,
        )
        is not None
    )


def build_session(
    extractor: StructuredExtractor | Extractor, repository: ProcedureRepository
) -> ConversationSession:
    return ConversationSession(extractor, repository)
