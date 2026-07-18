"""Suggestion-aware conversation session independent of terminal I/O."""

from __future__ import annotations

import math
import re
import unicodedata
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

from .replies import GroundedReply, ReplyComposer


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

    def __init__(
        self,
        extractor: Extractor,
        repository: ProcedureRepository,
        *,
        reply_composer: ReplyComposer | None = None,
    ) -> None:
        self._extractor = extractor
        self._repository = repository
        self._rules = RuleEngine(repository)
        self._questions = QuestionSelector(repository)
        self._reply_composer = reply_composer
        self._state = ConversationState()
        self._closed = False
        self._contextual_reference_trusted = False
        self._pending_scope_clarification: str | None = None
        self._birth_for_child = False

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
        self._contextual_reference_trusted = True

    def send(self, message: str) -> TurnResult:
        self._ensure_open()
        active_code = self._state.draft.procedure_code
        previous_missing = (
            self._rules.missing_fields(active_code, self._state.draft.values)
            if active_code is not None
            else ()
        )
        normalized = self._normalize_message(message)

        if active_code is not None and self._is_guided_form_help_request(normalized):
            self._contextual_reference_trusted = True
            prompt, action = self._resume_prompt(active_code)
            return self._reply_without_draft_change(
                message,
                f"Tôi sẽ hỏi từng mục một và chỉ điền sau khi bạn trả lời. {prompt}",
                action,
            )

        if self._is_small_talk(normalized):
            return self._small_talk_reply(message, normalized, active_code)

        if self._pending_scope_clarification == "birth":
            scope_choice = self._birth_scope_choice(normalized)
            if scope_choice == "copy":
                self._pending_scope_clarification = None
                return self._select_birth_copy(message, active_code)
            if scope_choice == "new_registration":
                self._pending_scope_clarification = None
                return self._reply_without_draft_change(
                    message,
                    "Đăng ký khai sinh mới chưa nằm trong ba thủ tục VNeGuide hỗ trợ. "
                    "Tôi chưa thay đổi hồ sơ hiện tại của bạn.",
                    NextAction.OUT_OF_SCOPE,
                )
            return self._reply_without_draft_change(
                message,
                "Tôi vẫn nhớ bạn đang chọn giữa hai việc. Bạn hãy chọn “Xin bản sao "
                "Giấy khai sinh” hoặc “Đăng ký khai sinh mới” nhé.",
                NextAction.ASK_CLARIFICATION,
            )

        if self._is_typo_birth_copy_request(normalized):
            return self._select_birth_copy(message, active_code)

        waiting_for_requester_type = (
            active_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
            and bool(previous_missing)
            and previous_missing[0] == "requester_type"
        )
        if waiting_for_requester_type and self._is_uncertain_answer(normalized):
            return self._reply_without_draft_change(
                message,
                "Không sao. Biểu mẫu hiện có ba lựa chọn: xin cho bản thân, người được "
                "ủy quyền, hoặc đại diện cơ quan/tổ chức. Tôi sẽ chưa tự điền khi bạn chưa "
                "chắc; bạn có thể chọn một phương án bên dưới hoặc hỏi cơ quan hộ tịch.",
                NextAction.ASK_CLARIFICATION,
            )
        if waiting_for_requester_type and self._mentions_child(normalized):
            self._birth_for_child = True
            self._contextual_reference_trusted = True
            return self._reply_without_draft_change(
                message,
                "Tôi đã ghi nhận bạn đang xin bản sao Giấy khai sinh cho con. "
                "Để không điền sai tư cách pháp lý, bạn hãy cho biết mình là người được "
                "ủy quyền hay đại diện cơ quan/tổ chức. Nếu chưa chắc, chọn “Tôi chưa rõ”.",
                NextAction.ASK_CLARIFICATION,
            )

        if self._needs_birth_scope_clarification(message):
            self._contextual_reference_trusted = False
            self._pending_scope_clarification = "birth"
            active_note = ""
            if active_code is not None:
                title = self._repository.get_by_code(active_code).procedure_name
                active_note = f" Phiên “{title}” hiện tại vẫn được giữ nguyên."
            return self._reply_without_draft_change(
                message,
                "“Làm giấy khai sinh” có thể là hai việc khác nhau. VNeGuide chỉ hỗ trợ "
                "cấp bản sao Trích lục hộ tịch (bản sao Giấy khai sinh), không hỗ trợ "
                "đăng ký khai sinh mới. Bạn muốn xin bản sao hay đăng ký khai sinh mới?"
                f"{active_note}",
                NextAction.ASK_CLARIFICATION,
            )
        if active_code is not None:
            contextual_reply = self._compose_contextual_grounded_reply(active_code, message)
            if contextual_reply is not None:
                self._contextual_reference_trusted = True
                reply, action = self._reply_for_grounded_guidance(contextual_reply)
                return self._finish_turn(
                    message,
                    reply,
                    action,
                    source_ids=contextual_reply.source_ids,
                )
        context = None
        if active_code is not None:
            expected_field = (
                previous_missing[0] if previous_missing and not self._pending() else None
            )
            context = ExtractionTurnContext(active_code.value, expected_field)
        outcome = self._extractor.extract(message, context=context)
        routing_text = (
            self._normalize_message(outcome.normalization.normalized_text)
            if outcome.normalization is not None
            else normalized
        )
        reviewed_match = self._reviewed_procedure_match(routing_text)
        if (
            outcome.succeeded
            and reviewed_match is not None
            and (
                outcome.classification in {"ambiguous", "unsupported"}
                or outcome.procedure_code is None
            )
        ):
            # A reviewed catalog alias is stronger routing evidence than an LLM
            # fallback classification. Keep extraction first so mixed turns can
            # still produce field suggestions, but never present an exact alias
            # of one of the three supported procedures as out of scope.
            outcome = ExtractionOutcome(
                status="success",
                classification="supported",
                procedure_code=reviewed_match.value,
                fields={},
                evidence={},
                clarification_question=None,
                attempts=outcome.attempts,
                normalization=outcome.normalization,
            )
        if not outcome.succeeded:
            return self._technical_fallback(message, outcome.error_code or "provider_error")
        self._clear_technical_failures()
        if outcome.classification == "unsupported":
            if not self._looks_like_service_request(normalized):
                return self._small_talk_reply(message, normalized, active_code)
            return self._unsupported(message)
        if outcome.classification == "ambiguous" or outcome.procedure_code is None:
            self._contextual_reference_trusted = False
            if (
                outcome.normalization is not None
                and outcome.normalization.ambiguities
                and outcome.clarification_question
            ):
                return self._reply_without_draft_change(
                    message,
                    outcome.clarification_question,
                    NextAction.ASK_CLARIFICATION,
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
            self._contextual_reference_trusted = False
            return self._reply_without_draft_change(
                message,
                "Yêu cầu mới thuộc thủ tục khác. Hãy dùng /reset trước khi chuyển thủ tục.",
                NextAction.ASK_CLARIFICATION,
            )
        self._contextual_reference_trusted = True

        draft = self._state.draft
        if current_code is None:
            pack = self._repository.get_by_code(code)
            draft = replace(draft, procedure_code=code, pack_version=pack.version)
            self._state = replace(self._state, draft=draft)
            confirmation = pack.routing.get("confirmation_message")
            reply = (
                confirmation
                if isinstance(confirmation, str) and confirmation.strip()
                else f"Bạn muốn thực hiện thủ tục “{pack.procedure_name}”, đúng không?"
            )
            return self._finish_turn(
                message,
                reply,
                NextAction.ASK_CLARIFICATION,
            )

        grounded_reply = self._compose_grounded_reply(code, message)

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
            if field_id == "requester_type":
                self._birth_for_child = False
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
        if previous_missing and not valid_fields and grounded_reply is None:
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
        if grounded_reply is not None:
            reply, action = self._reply_for_grounded_guidance(grounded_reply)
        elif pending:
            confirmation = (
                f"Tôi đã tạo {len(pending)} đề xuất. "
                "Hãy xác nhận, sửa hoặc bỏ từng đề xuất trước khi đi tiếp."
            )
            reply = confirmation
            action = NextAction.CONFIRM_SUGGESTION
        else:
            reply, action = self._next_prompt(code)
        return self._finish_turn(
            message,
            reply,
            action,
            extracted_fields=valid_fields,
            source_ids=(grounded_reply.source_ids if grounded_reply is not None else None),
        )

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
        code = self._state.draft.procedure_code
        if code is None:
            raise RuntimeError("Cannot reject a suggestion without a procedure")
        label = self._field_label(code, suggestion.field_id).lower()
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
        result = self._result_after_action(f"Đã bỏ đề xuất cho {label}.")
        return self._finish_turn(
            f"Bỏ đề xuất: {label}",
            result.reply,
            result.next_action,
        )

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
        if field_id == "requester_type":
            self._birth_for_child = False
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
        result = self._result_after_action(
            f"Đã ghi nhận {self._field_label(code, field_id).lower()}."
        )
        if user_message is None:
            return result
        return self._finish_turn(user_message, result.reply, result.next_action)

    def close(self) -> None:
        self._state = ConversationState()
        self._closed = True
        self._contextual_reference_trusted = False
        self._pending_scope_clarification = None
        self._birth_for_child = False

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
        label = self._field_label(code, suggestion.field_id).lower()
        result = self._result_after_action(f"{verb} {label}.")
        user_action = "Sửa và xác nhận" if status is SuggestionStatus.EDITED else "Xác nhận"
        return self._finish_turn(
            f"{user_action}: {label}",
            result.reply,
            result.next_action,
        )

    def _result_after_action(self, prefix: str) -> TurnResult:
        code = self._state.draft.procedure_code
        if code is None:
            raise RuntimeError("Conversation has no active procedure")
        self._contextual_reference_trusted = True
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
            question_id = self._question_id(code, field_id)
            if question_id not in self._state.asked_question_ids:
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
                f"Bạn còn {len(pending)} đề xuất cần xác nhận, sửa hoặc bỏ trước khi đi tiếp.",
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
        return self._build_result(
            reply,
            action,
            extracted_fields=extracted_fields,
            source_ids=source_ids,
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
            resolved_source_ids = source_ids
        return TurnResult(
            reply=reply,
            state=self._state,
            next_action=action,
            source_ids=resolved_source_ids,
            missing_fields=missing,
            validation=validation,
            extracted_fields={} if extracted_fields is None else extracted_fields,
        )

    def _technical_fallback(self, message: str, error_code: str) -> TurnResult:
        self._contextual_reference_trusted = False
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
        self._contextual_reference_trusted = False
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

    def _small_talk_reply(
        self,
        message: str,
        normalized: str,
        active_code: ProcedureCode | None,
    ) -> TurnResult:
        if "cam on" in normalized:
            opening = "Rất vui được hỗ trợ bạn."
        else:
            opening = "Xin chào! Tôi đang ở đây để hỗ trợ bạn."
        if active_code is None:
            return self._reply_without_draft_change(
                message,
                f"{opening} Bạn cần đăng ký tạm trú, xác nhận điều kiện nhà ở "
                "hay xin bản sao Giấy khai sinh?",
                NextAction.ASK_CLARIFICATION,
            )
        title = self._repository.get_by_code(active_code).procedure_name
        prompt, action = self._resume_prompt(active_code)
        return self._reply_without_draft_change(
            message,
            f"{opening} Tôi vẫn đang cùng bạn hoàn thành thủ tục “{title}”. {prompt}",
            action,
        )

    def _compose_grounded_reply(
        self,
        procedure_code: ProcedureCode,
        message: str,
    ) -> GroundedReply | None:
        if self._reply_composer is None:
            return None
        try:
            reply = self._reply_composer.compose(
                procedure_code=procedure_code,
                message=message,
            )
            return self._reviewed_grounded_reply(procedure_code, reply)
        except Exception:
            # Reply composition is optional. Extraction and the deterministic
            # state machine remain available if the presentation layer fails.
            return None

    def _compose_contextual_grounded_reply(
        self,
        procedure_code: ProcedureCode,
        message: str,
    ) -> GroundedReply | None:
        if self._reply_composer is None:
            return None
        compose_contextual = getattr(self._reply_composer, "compose_contextual", None)
        if not callable(compose_contextual):
            return None
        try:
            reply = compose_contextual(
                procedure_code=procedure_code,
                message=message,
                allow_implicit_context=self._contextual_reference_trusted,
            )
            if not isinstance(reply, GroundedReply):
                return None
            return self._reviewed_grounded_reply(procedure_code, reply)
        except Exception:
            return None

    def _reviewed_grounded_reply(
        self,
        procedure_code: ProcedureCode,
        reply: GroundedReply | None,
    ) -> GroundedReply | None:
        if reply is None:
            return None
        reviewed_sources = set(self._repository.get_by_code(procedure_code).source_ids)
        if not set(reply.source_ids).issubset(reviewed_sources):
            return None
        return reply

    def _reply_for_grounded_guidance(
        self,
        reply: GroundedReply,
    ) -> tuple[str, NextAction]:
        pending = self._pending()
        if not pending:
            return reply.text, NextAction.PRESENT_GUIDANCE
        confirmation = (
            f"Bạn còn {len(pending)} đề xuất cần Accept, Reject hoặc Edit trước khi đi tiếp."
        )
        return f"{reply.text}\n\n{confirmation}", NextAction.CONFIRM_SUGGESTION

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

    def _field_label(self, code: ProcedureCode, field_id: str) -> str:
        for field in self._repository.fields_for(code):
            if field.field_id == field_id:
                return field.label
        return "thông tin còn thiếu"

    def _select_birth_copy(
        self,
        message: str,
        active_code: ProcedureCode | None,
    ) -> TurnResult:
        code = ProcedureCode.BIRTH_CERTIFICATE_COPY
        if active_code is not None and active_code is not code:
            active_title = self._repository.get_by_code(active_code).procedure_name
            return self._reply_without_draft_change(
                message,
                f"Tôi đã hiểu bạn muốn xin bản sao Giấy khai sinh, nhưng phiên hiện tại "
                f"đang là “{active_title}”. Hãy mở đúng trang thủ tục cấp bản sao để bắt đầu "
                "mà không làm mất dữ liệu đang nhập.",
                NextAction.ASK_CLARIFICATION,
            )

        if active_code is None:
            pack = self._repository.get_by_code(code)
            self._state = replace(
                self._state,
                draft=replace(
                    self._state.draft,
                    procedure_code=code,
                    pack_version=pack.version,
                ),
            )
        self._contextual_reference_trusted = True
        if self._mentions_child(self._normalize_message(message)):
            self._birth_for_child = True
        reply, action = self._next_prompt(code)
        if self._birth_for_child:
            reply = f"Tôi đã ghi nhận bạn đang xin bản sao Giấy khai sinh cho con. {reply}"
        return self._finish_turn(message, reply, action)

    @staticmethod
    def _normalize_message(message: str) -> str:
        normalized = unicodedata.normalize("NFD", message.casefold())
        normalized = "".join(
            character for character in normalized if unicodedata.category(character) != "Mn"
        ).replace("đ", "d")
        return re.sub(r"[^a-z0-9]+", " ", normalized).strip()

    @staticmethod
    def _birth_scope_choice(normalized: str) -> str | None:
        if any(
            marker in normalized
            for marker in ("ban sao", "bao sao", "trich luc", "xin lai", "cap lai")
        ):
            return "copy"
        if any(
            marker in normalized
            for marker in ("dang ky khai sinh", "khai sinh moi", "moi sinh", "so sinh")
        ):
            return "new_registration"
        return None

    @staticmethod
    def _is_typo_birth_copy_request(normalized: str) -> bool:
        return "bao sao" in normalized and "giay khai sinh" in normalized

    @staticmethod
    def _mentions_child(normalized: str) -> bool:
        return any(
            marker in normalized
            for marker in ("con toi", "con cua toi", "cho con", "cho chau", "cua chau")
        )

    @staticmethod
    def _is_uncertain_answer(normalized: str) -> bool:
        return normalized in {
            "toi chua ro",
            "toi khong ro",
            "chua ro",
            "khong ro",
            "khong biet",
        }

    @staticmethod
    def _is_guided_form_help_request(normalized: str) -> bool:
        guidance_markers = (
            "huong dan",
            "giup toi dien",
            "giup minh dien",
            "khong biet dien",
            "khong biet nhap",
            "nho tro giup",
        )
        input_markers = ("dien", "nhap", "muc", "o ", "ho so", "tiep")
        return any(marker in normalized for marker in guidance_markers) and any(
            marker in normalized for marker in input_markers
        )

    @staticmethod
    def _is_small_talk(normalized: str) -> bool:
        return normalized in {
            "alo",
            "cam on",
            "cam on ban",
            "chao",
            "chao ban",
            "hello",
            "hi",
            "xin cam on",
            "xin chao",
            "ban an com chua",
            "ban co khoe khong",
            "ban khoe khong",
        }

    @staticmethod
    def _looks_like_service_request(normalized: str) -> bool:
        return any(
            marker in f" {normalized} "
            for marker in (
                " thu tuc ",
                " ho so ",
                " giay ",
                " trich luc ",
                " dang ky ",
                " xac nhan ",
                " xin ",
                " cap ",
                " nop ",
                " doi ",
                " lam ",
            )
        )

    def _reviewed_procedure_match(self, normalized: str) -> ProcedureCode | None:
        """Resolve an explicit reviewed procedure alias without inventing new scope."""

        padded_message = f" {normalized} "
        matches: set[ProcedureCode] = set()
        for pack in self._repository.list_procedures():
            raw_aliases = pack.routing.get("aliases")
            aliases = (
                tuple(alias for alias in raw_aliases if isinstance(alias, str))
                if isinstance(raw_aliases, tuple)
                else ()
            )
            for candidate in (pack.procedure_name, *aliases):
                normalized_candidate = self._normalize_message(candidate)
                variants = {normalized_candidate}
                if normalized_candidate.startswith("xin "):
                    remainder = normalized_candidate.removeprefix("xin ")
                    variants.update({f"cap {remainder}", f"lam {remainder}"})
                if any(f" {variant} " in padded_message for variant in variants if variant):
                    matches.add(pack.procedure_code)
                    break
        return next(iter(matches)) if len(matches) == 1 else None

    @staticmethod
    def _needs_birth_scope_clarification(message: str) -> bool:
        """Fail closed for the common phrase that names two different services."""

        normalized = ConversationSession._normalize_message(message)

        explicit_copy_markers = (
            "ban sao",
            "trich luc",
            "xin lai",
            "cap lai",
            "mat giay khai sinh",
        )
        explicit_new_registration_markers = (
            "dang ky khai sinh",
            "moi sinh",
            "so sinh",
        )
        explicit_markers = (*explicit_copy_markers, *explicit_new_registration_markers)
        if any(marker in normalized for marker in explicit_markers):
            return False

        generic_birth_request = re.fullmatch(
            r"(?:(?:toi|minh|em|anh|chi|chung toi|gia dinh toi)\s+)?"
            r"(?:(?:dang\s+)?(?:muon|can)\s+)?"
            r"(?:lam|xin|cap)?\s*giay khai sinh"
            r"(?:\s+cho\s+(?:toi|ban than|con|con toi|be|be nha toi))?",
            normalized,
        )
        return generic_birth_request is not None

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Conversation session is closed")


def build_session(
    extractor: StructuredExtractor | Extractor,
    repository: ProcedureRepository,
    *,
    reply_composer: ReplyComposer | None = None,
) -> ConversationSession:
    return ConversationSession(extractor, repository, reply_composer=reply_composer)
