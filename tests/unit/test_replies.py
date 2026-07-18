from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from vneguide.ai import ExtractionOutcome, ExtractionTurnContext
from vneguide.ai.schemas import JsonScalar
from vneguide.core import (
    CatalogReplyComposer,
    ConversationSession,
    GroundedReply,
    GuidanceTopic,
    ProcedureConflictError,
    RevisionConflictError,
    build_session,
)
from vneguide.data import ProcedureRepository
from vneguide.domain import (
    CaseDraft,
    ConversationState,
    FieldSuggestion,
    JSONValue,
    NextAction,
    ProcedureCode,
    SuggestionStatus,
    ValidationResult,
    ValidationStatus,
)

ROOT = Path(__file__).resolve().parents[2]


class StubExtractor:
    def __init__(self, *outcomes: ExtractionOutcome) -> None:
        self._outcomes = deque(outcomes)

    def extract(
        self,
        _message: str,
        *,
        context: ExtractionTurnContext | None = None,
    ) -> ExtractionOutcome:
        del context
        return self._outcomes.popleft()


def outcome(
    code: str | None,
    *,
    classification: str = "supported",
    fields: Mapping[str, JsonScalar] | None = None,
) -> ExtractionOutcome:
    actual_fields = {} if fields is None else fields
    return ExtractionOutcome(
        status="success",
        classification=classification,
        procedure_code=code,
        fields=actual_fields,
        evidence={field_id: f"evidence:{field_id}" for field_id in actual_fields},
        clarification_question=None,
        attempts=1,
    )


@pytest.fixture(scope="module")
def repository() -> ProcedureRepository:
    return ProcedureRepository.discover(ROOT)


@pytest.mark.parametrize(
    ("message", "topic", "expected_text"),
    (
        ("Lệ phí bao nhiêu?", GuidanceTopic.FEE, "8.000 đồng"),
        ("Mất bao lâu?", GuidanceTopic.PROCESSING_TIME, "Theo phiếu hẹn"),
        ("Cần những giấy tờ gì?", GuidanceTopic.CHECKLIST, "Thông tin số định danh"),
        ("Hướng dẫn các bước", GuidanceTopic.STEPS, "1. Xác nhận"),
        ("Nộp ở đâu?", GuidanceTopic.AUTHORITY, "Cơ quan quản lý"),
        ("Có nộp online được không?", GuidanceTopic.CHANNELS, "qua bưu chính"),
        ("Tôi nhận được gì?", GuidanceTopic.RESULT, "bản sao Giấy khai sinh"),
    ),
)
def test_composer_answers_allowlisted_topics_from_reviewed_catalog(
    repository: ProcedureRepository,
    message: str,
    topic: GuidanceTopic,
    expected_text: str,
) -> None:
    composer = CatalogReplyComposer(repository)

    reply = composer.compose(
        procedure_code=ProcedureCode("2.000635"),
        message=message,
    )

    assert reply is not None
    assert reply.topic is topic
    assert expected_text in reply.text
    assert set(reply.source_ids) <= set(repository.get_by_code("2.000635").source_ids)


@pytest.mark.parametrize(
    ("code", "fee_text", "time_text", "authority_text"),
    (
        ("2.000635", "8.000 đồng", "Theo phiếu hẹn", "Cơ quan quản lý"),
        ("1.013314", "Không thu phí", "02 ngày làm việc", "Ủy ban nhân dân"),
        ("1.004194", "7.000 đồng", "03 ngày làm việc", "Công an cấp xã"),
    ),
)
def test_composer_uses_the_selected_procedure_pack(
    repository: ProcedureRepository,
    code: str,
    fee_text: str,
    time_text: str,
    authority_text: str,
) -> None:
    composer = CatalogReplyComposer(repository)

    replies = (
        composer.compose(procedure_code=ProcedureCode(code), message="Lệ phí bao nhiêu?"),
        composer.compose(procedure_code=ProcedureCode(code), message="Mất bao lâu?"),
        composer.compose(procedure_code=ProcedureCode(code), message="Nộp ở đâu?"),
    )

    assert replies[0] is not None and fee_text in replies[0].text
    assert replies[1] is not None and time_text in replies[1].text
    assert replies[2] is not None and authority_text in replies[2].text


def test_composer_ignores_free_chat_and_prioritizes_one_topic(
    repository: ProcedureRepository,
) -> None:
    composer = CatalogReplyComposer(repository)

    assert (
        composer.compose(
            procedure_code=ProcedureCode("1.004194"),
            message="Hôm nay trời đẹp không?",
        )
        is None
    )
    selected = composer.compose(
        procedure_code=ProcedureCode("1.004194"),
        message="Lệ phí bao nhiêu và mất bao lâu?",
    )
    assert selected is not None
    assert selected.topic is GuidanceTopic.FEE
    assert "03 ngày" not in selected.text


def test_composer_ignores_empty_input(repository: ProcedureRepository) -> None:
    composer = CatalogReplyComposer(repository)

    assert (
        composer.compose(
            procedure_code=ProcedureCode("1.004194"),
            message="   ",
        )
        is None
    )


def test_composer_fails_closed_for_invalid_reviewed_service_data(
    repository: ProcedureRepository,
) -> None:
    composer = CatalogReplyComposer(repository)
    pack = repository.get_by_code("1.004194")

    with pytest.raises(ValueError, match="channels"):
        composer._render(  # noqa: SLF001 - corruption boundary test
            GuidanceTopic.CHANNELS,
            replace(pack, service_info={"channels": "online"}),
        )
    with pytest.raises(ValueError, match="channels"):
        composer._render(  # noqa: SLF001 - corruption boundary test
            GuidanceTopic.CHANNELS,
            replace(pack, service_info={"channels": []}),
        )
    with pytest.raises(ValueError, match="service_info.result"):
        composer._render(  # noqa: SLF001 - corruption boundary test
            GuidanceTopic.RESULT,
            replace(pack, service_info={"result": ""}),
        )
    with pytest.raises(AssertionError, match="unsupported"):
        composer._render(
            cast(Any, "not_allowlisted"),
            pack,
        )


def test_fee_renderer_validates_all_supported_shapes(
    repository: ProcedureRepository,
) -> None:
    composer = CatalogReplyComposer(repository)
    pack = repository.get_by_code("1.004194")

    amount_only = replace(pack, service_info={"fee": {"amount_vnd": 1200}})
    no_exemption = replace(
        pack,
        service_info={
            "fee": {
                "individual_or_household": {
                    "online_vnd": 7000,
                    "direct_vnd": 15000,
                }
            }
        },
    )
    assert composer._render_fee(amount_only) == "Lệ phí: 1.200 đồng."  # noqa: SLF001
    assert "7.000 đồng" in composer._render_fee(no_exemption)  # noqa: SLF001

    invalid_fees: tuple[tuple[JSONValue, str], ...] = (
        ("unknown", "object"),
        (
            {"individual_or_household": {"online_vnd": True, "direct_vnd": -1}},
            "individual fee",
        ),
        ({}, "supported display"),
    )
    for fee, error in invalid_fees:
        invalid_pack = replace(pack, service_info={"fee": fee})
        with pytest.raises(ValueError, match=error):
            composer._render_fee(invalid_pack)  # noqa: SLF001


def test_empty_checklist_cannot_produce_ungrounded_guidance(
    repository: ProcedureRepository,
) -> None:
    composer = CatalogReplyComposer(repository)
    pack = replace(repository.get_by_code("1.004194"), checklist=())

    with pytest.raises(ValueError, match="no reviewed sources"):
        composer._render(GuidanceTopic.CHECKLIST, pack)  # noqa: SLF001


def test_guidance_only_turn_preserves_workflow_state(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(outcome("1.004194"), outcome("1.004194")),
        repository,
        reply_composer=CatalogReplyComposer(repository),
    )
    first = session.send("Tôi muốn đăng ký tạm trú")
    before = session.state

    result = session.send("Lệ phí bao nhiêu?")

    assert first.next_action is NextAction.ASK_CLARIFICATION
    assert result.next_action is NextAction.PRESENT_GUIDANCE
    assert "7.000 đồng" in result.reply
    assert result.state.draft == before.draft
    assert result.state.suggestions == before.suggestions
    assert result.state.clarification_attempts == before.clarification_attempts
    assert result.state.asked_question_ids == before.asked_question_ids
    assert result.state.turn_number == before.turn_number + 1


def test_mixed_guidance_and_field_extraction_keeps_suggestion_contract(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(
                "1.004194",
                fields={"submission_channel": "online"},
            )
        ),
        repository,
        reply_composer=CatalogReplyComposer(repository),
    )

    result = session.send("Tôi nộp online, lệ phí bao nhiêu?")

    assert result.next_action is NextAction.CONFIRM_SUGGESTION
    assert "7.000 đồng" in result.reply
    assert "1 đề xuất" in result.reply
    assert result.draft == {}
    assert result.suggestions[-1].field_id == "submission_channel"
    assert result.suggestions[-1].suggested_value == "online"


class FailingComposer:
    def compose(
        self,
        *,
        procedure_code: ProcedureCode,
        message: str,
    ) -> GroundedReply | None:
        del procedure_code, message
        raise RuntimeError("synthetic composer failure")


class UnreviewedSourceComposer:
    def compose(
        self,
        *,
        procedure_code: ProcedureCode,
        message: str,
    ) -> GroundedReply | None:
        del procedure_code, message
        return GroundedReply(
            text="Nội dung không được phép hiển thị.",
            topic=GuidanceTopic.FEE,
            source_ids=("SRC-NOT-REVIEWED",),
        )


@pytest.mark.parametrize("composer", (FailingComposer(), UnreviewedSourceComposer()))
def test_optional_composer_failure_falls_back_to_existing_flow(
    repository: ProcedureRepository,
    composer: FailingComposer | UnreviewedSourceComposer,
) -> None:
    session = ConversationSession(
        StubExtractor(outcome("1.004194")),
        repository,
        reply_composer=composer,
    )

    result = session.send("Lệ phí bao nhiêu?")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "hình thức đăng ký" in result.reply.lower()
    assert "không được phép" not in result.reply


def test_unsupported_classification_cannot_be_overridden_by_guidance(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(outcome(None, classification="unsupported")),
        repository,
        reply_composer=CatalogReplyComposer(repository),
    )

    result = session.send("Lệ phí đăng ký kết hôn bao nhiêu?")

    assert result.next_action is NextAction.OUT_OF_SCOPE
    assert result.draft == {}
    assert "8.000" not in result.reply
    assert "7.000" not in result.reply


def test_pending_suggestions_remain_the_priority_after_out_of_scope_turn(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome("2.000635", fields={"copies_requested": 1}),
            outcome(None, classification="unsupported"),
        ),
        repository,
        reply_composer=CatalogReplyComposer(repository),
    )
    first = session.send("Tôi xin một bản")

    result = session.send("Phí đăng ký kết hôn bao nhiêu?")

    assert first.next_action is NextAction.CONFIRM_SUGGESTION
    assert result.next_action is NextAction.OUT_OF_SCOPE
    assert "1 đề xuất" in result.reply
    assert result.state.suggestions == first.state.suggestions


def test_procedure_initialization_is_idempotent_and_rejects_switch(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(StubExtractor(), repository)

    session.initialize_procedure("1.004194")
    initial_state = session.state
    session.initialize_procedure("1.004194")

    assert session.state == initial_state
    with pytest.raises(ProcedureConflictError):
        session.initialize_procedure("2.000635")


class StubRules:
    def __init__(self, status: ValidationStatus) -> None:
        self._status = status

    def missing_fields(
        self,
        _procedure_code: ProcedureCode,
        _values: Mapping[str, object],
    ) -> tuple[str, ...]:
        return ()

    def validate(
        self,
        procedure_code: ProcedureCode,
        _values: Mapping[str, object],
    ) -> ValidationResult:
        return ValidationResult(
            procedure_code=procedure_code,
            status=self._status,
            issues=(),
            passed_checks=("synthetic-status-mapping",),
            source_ids=("SRC-DVC-1004194",),
        )


@pytest.mark.parametrize(
    ("status", "expected_action"),
    (
        (ValidationStatus.NEEDS_CORRECTION, NextAction.REQUEST_CORRECTION),
        (ValidationStatus.NEEDS_OFFICIAL_REVIEW, NextAction.REQUEST_OFFICIAL_REVIEW),
        (ValidationStatus.OUT_OF_SCOPE, NextAction.OUT_OF_SCOPE),
    ),
)
def test_next_prompt_maps_fail_closed_validation_states(
    repository: ProcedureRepository,
    status: ValidationStatus,
    expected_action: NextAction,
) -> None:
    session = ConversationSession(StubExtractor(), repository)
    session._rules = cast(Any, StubRules(status))  # noqa: SLF001 - state mapping unit test

    reply, action = session._next_prompt(  # noqa: SLF001 - state mapping unit test
        ProcedureCode("1.004194")
    )

    assert reply
    assert action is expected_action


def test_build_session_keeps_the_optional_reply_composer(
    repository: ProcedureRepository,
) -> None:
    session = build_session(
        StubExtractor(outcome("1.004194")),
        repository,
        reply_composer=CatalogReplyComposer(repository),
    )

    assert session.send("Mất bao lâu?").next_action is NextAction.PRESENT_GUIDANCE


def test_suggestion_resolution_rejects_inconsistent_internal_state(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(StubExtractor(), repository)
    stale = FieldSuggestion(
        suggestion_id="stale",
        field_id="submission_channel",
        current_value=None,
        suggested_value="online",
        evidence="synthetic",
        status=SuggestionStatus.PENDING,
        revision=0,
    )
    session._state = ConversationState(  # noqa: SLF001 - invariant corruption test
        draft=CaseDraft(
            procedure_code=ProcedureCode("1.004194"),
            revision=1,
            pack_version=repository.get_by_code("1.004194").version,
        ),
        suggestions=(stale,),
    )

    with pytest.raises(RevisionConflictError, match="stale"):
        session.accept_suggestion("stale", expected_revision=1)

    session._state = ConversationState(suggestions=(replace(stale, suggestion_id="orphan"),))  # noqa: SLF001
    with pytest.raises(RuntimeError, match="without a procedure"):
        session.accept_suggestion("orphan", expected_revision=0)


def test_internal_action_helpers_guard_impossible_arguments(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(StubExtractor(), repository)

    with pytest.raises(RuntimeError, match="no active procedure"):
        session._result_after_action("synthetic")  # noqa: SLF001 - invariant guard test
    with pytest.raises(AssertionError, match="provided together"):
        session._rebase_suggestions(  # noqa: SLF001 - invariant guard test
            1,
            resolved_id="missing-status",
        )


def test_grounded_reply_requires_text_and_sources() -> None:
    with pytest.raises(ValueError, match="text"):
        GroundedReply(text=" ", topic=GuidanceTopic.FEE, source_ids=("SRC",))
    with pytest.raises(ValueError, match="sources"):
        GroundedReply(text="Có nội dung", topic=GuidanceTopic.FEE, source_ids=())
    with pytest.raises(ValueError, match="sources"):
        GroundedReply(text="Có nội dung", topic=GuidanceTopic.FEE, source_ids=(" ",))
