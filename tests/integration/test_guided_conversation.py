from __future__ import annotations

from collections import deque
from pathlib import Path

from vneguide.ai import ExtractionOutcome, ExtractionTurnContext
from vneguide.ai.schemas import JsonScalar
from vneguide.core import ConversationSession
from vneguide.data import ProcedureRepository
from vneguide.domain import NextAction, SuggestionStatus

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ACTIONS = {
    "confirm_procedure",
    "choose_portal",
    "fill_missing_field",
    "review_suggestion",
    "upload_document",
    "fix_validation",
    "ready_to_continue",
    "needs_official_review",
    "unsupported",
}

COMPLETE_BIRTH_COPY: dict[str, JsonScalar] = {
    "requester_type": "self",
    "requester_full_name": "Người Yêu Cầu Kiểm Thử",
    "requester_personal_id": "000000000000",
    "subject_full_name": "Người Được Trích Lục Kiểm Thử",
    "subject_date_of_birth": "2000-01-01",
    "copies_requested": 1,
    "submission_channel": "online",
}


class ScriptedExtractor:
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


def supported(fields: dict[str, JsonScalar]) -> ExtractionOutcome:
    return ExtractionOutcome(
        status="success",
        classification="supported",
        procedure_code="2.000635",
        fields=fields,
        evidence={field_id: f"synthetic:{field_id}" for field_id in fields},
        clarification_question=None,
        attempts=1,
    )


def test_guided_golden_flow_reviews_all_fields_then_stops_asking() -> None:
    repository = ProcedureRepository.discover(ROOT)
    session = ConversationSession(
        ScriptedExtractor(supported(COMPLETE_BIRTH_COPY)),
        repository,
    )
    session.initialize_procedure("2.000635")

    results = [session.send("Tôi cung cấp toàn bộ thông tin tổng hợp trong một lượt.")]
    while pending := [
        item for item in results[-1].suggestions if item.status is SuggestionStatus.PENDING
    ]:
        results.append(
            session.accept_suggestion(
                pending[0].suggestion_id,
                expected_revision=results[-1].state.draft.revision,
            )
        )

    assert results[0].next_action is NextAction.REVIEW_SUGGESTION
    assert set(results[0].extracted_fields) == set(COMPLETE_BIRTH_COPY)
    assert results[-1].next_action is NextAction.READY_TO_CONTINUE
    assert results[-1].missing_fields == ()
    assert all(result.next_action.value in ALLOWED_ACTIONS for result in results)
    assert session.state.turn_number <= 6
