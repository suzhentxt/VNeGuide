from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest

from vneguide.ai import ExtractionOutcome
from vneguide.core import ConversationSession
from vneguide.data import ProcedureRepository
from vneguide.domain import NextAction, SuggestionStatus

ROOT = Path(__file__).resolve().parents[2]


class StubExtractor:
    def __init__(self, *outcomes: ExtractionOutcome) -> None:
        self.outcomes = deque(outcomes)

    def extract(self, _message: str) -> ExtractionOutcome:
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
    accepted = session.accept_suggestion(first.suggestion_id)
    assert accepted.draft[first.field_id] == first.suggested_value
    assert accepted.suggestions[0].status is SuggestionStatus.ACCEPTED

    with pytest.raises(ValueError, match="Unknown"):
        session.edit_suggestion(second.suggestion_id, "direct")
    rebased_second = next(
        item for item in accepted.suggestions if item.status is SuggestionStatus.PENDING
    )
    edited = session.edit_suggestion(rebased_second.suggestion_id, "direct")
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
    rejected = session.reject_suggestion(result.suggestions[0].suggestion_id)
    assert rejected.draft == {}
    assert rejected.suggestions[0].status is SuggestionStatus.REJECTED


def test_missing_answer_switches_to_manual_input_after_two_turns(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(fields={"copies_requested": 1}),
            outcome(fields={}),
            outcome(fields={}),
        ),
        repository,
    )
    initial = session.send("Xin một bản")
    session.accept_suggestion(initial.suggestions[0].suggestion_id)
    assert session.send("Tôi chưa rõ").next_action is NextAction.ASK_CLARIFICATION
    assert session.send("Tôi vẫn chưa rõ").next_action is NextAction.MANUAL_INPUT


def test_confirmed_field_is_never_overwritten(repository: ProcedureRepository) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(fields={"copies_requested": 1}),
            outcome(fields={"copies_requested": 3}),
        ),
        repository,
    )
    first = session.send("Một bản")
    session.accept_suggestion(first.suggestions[0].suggestion_id)
    conflict = session.send("Đổi thành ba bản")
    assert conflict.draft["copies_requested"] == 1
    assert conflict.suggestions[-1].current_value == 1
    assert conflict.suggestions[-1].suggested_value == 3


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
