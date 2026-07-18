from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest

from vneguide.ai import ExtractionOutcome, ExtractionTurnContext
from vneguide.core import ConversationSession, RevisionConflictError
from vneguide.data import ProcedureRepository
from vneguide.domain import NextAction, SuggestionStatus

ROOT = Path(__file__).resolve().parents[2]


class StubExtractor:
    def __init__(self, *outcomes: ExtractionOutcome) -> None:
        self.outcomes = deque(outcomes)
        self.calls: list[tuple[str, ExtractionTurnContext | None]] = []

    def extract(
        self,
        message: str,
        *,
        context: ExtractionTurnContext | None = None,
    ) -> ExtractionOutcome:
        self.calls.append((message, context))
        return self.outcomes.popleft()


def outcome(
    *,
    classification: str = "supported",
    procedure_code: str | None = "2.000635",
    fields: dict[str, object] | None = None,
    evidence: dict[str, str] | None = None,
    status: str = "success",
    error_code: str | None = None,
) -> ExtractionOutcome:
    return ExtractionOutcome(
        status=status,
        classification=classification if status == "success" else None,
        procedure_code=procedure_code if status == "success" else None,
        fields={} if fields is None else fields,  # type: ignore[arg-type]
        evidence={} if evidence is None else evidence,
        clarification_question="Bạn muốn làm thủ tục nào?"
        if classification == "ambiguous"
        else None,
        attempts=1,
        error_code=error_code,
    )


@pytest.fixture(scope="module")
def repository() -> ProcedureRepository:
    return ProcedureRepository.discover(ROOT)


def test_fields_remain_pending_until_accept_and_edit(repository: ProcedureRepository) -> None:
    extractor = StubExtractor(
        outcome(
            fields={"copies_requested": 2, "submission_channel": "online"},
            evidence={"copies_requested": "2 bản", "submission_channel": "trực tuyến"},
        )
    )
    session = ConversationSession(extractor, repository)
    result = session.send("Tôi xin 2 bản trực tuyến")

    assert result.next_action is NextAction.CONFIRM_SUGGESTION
    assert result.draft == {}
    assert len(result.suggestions) == 2

    first, second = result.suggestions
    accepted = session.accept_suggestion(first.suggestion_id, expected_revision=0)
    assert accepted.draft[first.field_id] == first.suggested_value
    assert accepted.suggestions[0].status is SuggestionStatus.ACCEPTED

    with pytest.raises(ValueError, match="Unknown"):
        session.edit_suggestion(second.suggestion_id, "direct", expected_revision=1)
    rebased_second = next(
        item for item in accepted.suggestions if item.status is SuggestionStatus.PENDING
    )
    edited = session.edit_suggestion(
        rebased_second.suggestion_id,
        "direct",
        expected_revision=1,
    )
    assert edited.draft[second.field_id] == "direct"
    assert second.field_id in edited.state.draft.dirty_fields
    assert edited.state.draft.revision == 2


def test_reject_does_not_change_draft_and_caps_retries(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(outcome(fields={"copies_requested": 1})), repository
    )
    result = session.send("Một bản")
    rejected = session.reject_suggestion(
        result.suggestions[0].suggestion_id,
        expected_revision=0,
    )
    assert rejected.draft == {}
    assert rejected.state.draft.revision == 1
    assert rejected.suggestions[0].status is SuggestionStatus.REJECTED


def test_missing_answer_switches_to_manual_input_without_repeating_question(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(fields={"copies_requested": 1}),
            outcome(fields={}),
        ),
        repository,
    )
    initial = session.send("Xin một bản")
    accepted = session.accept_suggestion(
        initial.suggestions[0].suggestion_id,
        expected_revision=0,
    )
    question = accepted.reply
    manual = session.send("Tôi chưa rõ")
    assert manual.next_action is NextAction.MANUAL_INPUT
    assert question not in manual.reply


def test_confirmed_field_is_never_overwritten(repository: ProcedureRepository) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(fields={"copies_requested": 1}),
            outcome(fields={"copies_requested": 3}),
        ),
        repository,
    )
    first = session.send("Một bản")
    session.accept_suggestion(first.suggestions[0].suggestion_id, expected_revision=0)
    conflict = session.send("Đổi thành ba bản")
    assert conflict.draft["copies_requested"] == 1
    assert not [
        item
        for item in conflict.suggestions
        if item.status is SuggestionStatus.PENDING and item.field_id == "copies_requested"
    ]


def test_manual_edit_is_confirmed_dirty_and_revision_guarded(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(StubExtractor(), repository)
    session.initialize_procedure("1.004194")

    edited = session.edit_field(
        "submission_channel",
        "online",
        expected_revision=0,
    )

    assert edited.draft["submission_channel"] == "online"
    assert edited.state.draft.revision == 1
    assert "submission_channel" in edited.state.draft.confirmed_fields
    assert "submission_channel" in edited.state.draft.dirty_fields
    with pytest.raises(RevisionConflictError):
        session.edit_field(
            "submission_channel",
            "direct",
            expected_revision=0,
        )
    assert session.state.draft.values["submission_channel"] == "online"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_manual_edit_rejects_non_finite_number_without_mutation(
    repository: ProcedureRepository,
    value: float,
) -> None:
    session = ConversationSession(StubExtractor(), repository)
    session.initialize_procedure("1.013314")
    initial_state = session.state

    with pytest.raises(ValueError, match="finite number"):
        session.edit_field("floor_area_m2", value, expected_revision=0)

    assert session.state == initial_state


def test_ai_cannot_propose_an_overwrite_for_a_dirty_field(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(
                procedure_code="1.004194",
                fields={"submission_channel": "direct"},
                evidence={"submission_channel": "trực tiếp"},
            )
        ),
        repository,
    )
    session.initialize_procedure("1.004194")
    session.edit_field("submission_channel", "online", expected_revision=0)

    result = session.send("Tôi muốn đổi sang nộp trực tiếp")

    assert result.draft["submission_channel"] == "online"
    assert not [
        item
        for item in result.suggestions
        if item.status is SuggestionStatus.PENDING and item.field_id == "submission_channel"
    ]


def test_reject_increments_revision_and_rebases_other_pending_suggestions(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(
                fields={"copies_requested": 2, "submission_channel": "online"},
                evidence={"copies_requested": "2 bản", "submission_channel": "trực tuyến"},
            )
        ),
        repository,
    )
    turn = session.send("Tôi xin 2 bản trực tuyến")
    rejected_id = turn.suggestions[0].suggestion_id

    result = session.reject_suggestion(rejected_id, expected_revision=0)

    assert result.state.draft.revision == 1
    remaining = [item for item in result.suggestions if item.status is SuggestionStatus.PENDING]
    assert len(remaining) == 1
    assert remaining[0].revision == 1
    assert remaining[0].suggestion_id.startswith("1:")


def test_ambiguous_unsupported_and_fallback_do_not_populate_draft(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(classification="ambiguous", procedure_code=None),
            outcome(classification="unsupported", procedure_code=None),
            outcome(status="fallback", error_code="provider_timeout"),
            outcome(status="fallback", error_code="provider_timeout"),
        ),
        repository,
    )
    assert session.send("Giấy tờ cư trú").next_action is NextAction.ASK_CLARIFICATION
    unsupported = session.send("Trích lục kết hôn")
    assert unsupported.procedure_type == "out_of_scope"
    assert unsupported.draft == {}
    assert session.send("thử lại").next_action is NextAction.RETRY
    assert session.send("thử lại lần nữa").next_action is NextAction.MANUAL_INPUT


def test_successful_extraction_resets_non_consecutive_provider_failures(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(status="fallback", error_code="provider_timeout"),
            outcome(procedure_code="1.004194", fields={}),
            outcome(status="fallback", error_code="provider_timeout"),
        ),
        repository,
    )

    assert session.send("thử lần một").next_action is NextAction.RETRY
    session.send("Tôi muốn đăng ký tạm trú")
    assert session.send("thử sau khi thành công").next_action is NextAction.RETRY


def test_invalid_extracted_field_is_ignored_without_breaking_the_draft(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(
                procedure_code="2.000635",
                fields={"subject_date_of_birth": "2999-01-01"},
                evidence={"subject_date_of_birth": "2999-01-01"},
            )
        ),
        repository,
    )

    result = session.send("Ngày sinh là 2999-01-01")

    assert result.state.draft.procedure_code is not None
    assert result.draft == {}
    assert result.extracted_fields == {}
    assert not result.suggestions


def test_active_procedure_context_survives_an_unsupported_turn(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(procedure_code="1.004194", fields={}),
        outcome(classification="unsupported", procedure_code=None),
        outcome(
            procedure_code="1.004194",
            fields={"submission_channel": "online"},
            evidence={"submission_channel": "trực tuyến"},
        ),
    )
    session = ConversationSession(extractor, repository)

    initial = session.send("Tôi muốn đăng ký tạm trú")
    unsupported = session.send("Bạn ăn cơm chưa?")
    continued = session.send("Tôi đăng ký trực tuyến")

    assert initial.next_action is NextAction.ASK_CLARIFICATION
    assert "hình thức đăng ký" in initial.reply.lower()
    assert extractor.calls[0][1] is None
    for _, context in extractor.calls[1:]:
        assert context is not None
        assert context.active_procedure_code == "1.004194"
        assert context.expected_field_id == "registration_mode"
    assert unsupported.next_action is NextAction.OUT_OF_SCOPE
    assert "vẫn được giữ nguyên" in unsupported.reply
    assert "nhập trực tiếp trường registration_mode" in unsupported.reply.lower()
    assert continued.next_action is NextAction.CONFIRM_SUGGESTION
    assert continued.suggestions[-1].field_id == "submission_channel"


def test_active_ambiguous_turn_uses_the_deterministic_pending_question(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(procedure_code="1.004194", fields={}),
        outcome(classification="ambiguous", procedure_code=None),
        outcome(classification="ambiguous", procedure_code=None),
    )
    session = ConversationSession(extractor, repository)
    session.send("Tôi muốn đăng ký tạm trú")

    result = session.send("Tôi chưa rõ")
    manual = session.send("Vẫn chưa rõ")

    assert result.next_action is NextAction.MANUAL_INPUT
    assert "nhập trực tiếp trường registration_mode" in result.reply
    assert "Bạn muốn làm thủ tục nào?" not in result.reply
    assert extractor.calls[-1][1] == ExtractionTurnContext(
        active_procedure_code="1.004194",
        expected_field_id="registration_mode",
    )
    assert manual.next_action is NextAction.MANUAL_INPUT
    assert "nhập trực tiếp trường registration_mode" in manual.reply


def test_birth_copy_follow_ups_keep_the_active_procedure_without_inference(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(procedure_code="2.000635", fields={}),
        outcome(procedure_code="2.000635", fields={}),
        outcome(
            procedure_code="2.000635",
            fields={"submission_channel": "online"},
            evidence={"submission_channel": "trực tuyến"},
        ),
    )
    session = ConversationSession(extractor, repository)

    session.send("Tôi cần cấp bản sao Giấy khai sinh")
    relationship = session.send("Cho con tôi")
    channel = session.send("Đăng ký trực tuyến")

    assert relationship.next_action is NextAction.MANUAL_INPUT
    assert "nhập trực tiếp trường requester_type" in relationship.reply
    assert relationship.state.draft.procedure_code is not None
    assert relationship.state.draft.procedure_code.value == "2.000635"
    assert channel.next_action is NextAction.CONFIRM_SUGGESTION
    assert channel.suggestions[-1].field_id == "submission_channel"
    accepted = session.accept_suggestion(
        channel.suggestions[-1].suggestion_id,
        expected_revision=0,
    )
    assert accepted.next_action is NextAction.MANUAL_INPUT
    assert "nhập trực tiếp trường requester_type" in accepted.reply
    assert [call[1] for call in extractor.calls] == [
        None,
        ExtractionTurnContext("2.000635", "requester_type"),
        ExtractionTurnContext("2.000635", "requester_type"),
    ]


def test_switching_procedure_requires_reset(repository: ProcedureRepository) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(fields={"copies_requested": 1}),
            outcome(procedure_code="1.004194", fields={"submission_channel": "online"}),
        ),
        repository,
    )
    session.send("Xin một bản")
    result = session.send("Tôi muốn đăng ký tạm trú")
    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert result.state.draft.procedure_code is not None
    assert result.state.draft.procedure_code.value == "2.000635"


def test_close_clears_state_and_prevents_reuse(repository: ProcedureRepository) -> None:
    session = ConversationSession(StubExtractor(), repository)
    session.close()
    assert session.state.turn_number == 0
    with pytest.raises(RuntimeError, match="closed"):
        session.send("không được xử lý")
