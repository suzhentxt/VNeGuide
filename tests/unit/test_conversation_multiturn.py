from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from vneguide.ai import ExtractionOutcome, ExtractionTurnContext
from vneguide.ai.schemas import JsonScalar
from vneguide.core import ConversationSession
from vneguide.data import ProcedureRepository
from vneguide.domain import NextAction, SuggestionStatus

ROOT = Path(__file__).resolve().parents[2]


class StubExtractor:
    def __init__(self, *outcomes: ExtractionOutcome) -> None:
        self._outcomes = deque(outcomes)
        self.calls: list[tuple[str, ExtractionTurnContext | None]] = []

    def extract(
        self,
        message: str,
        *,
        context: ExtractionTurnContext | None = None,
    ) -> ExtractionOutcome:
        self.calls.append((message, context))
        return self._outcomes.popleft()


def outcome(
    code: str | None,
    *,
    classification: str = "supported",
    fields: Mapping[str, JsonScalar] | None = None,
) -> ExtractionOutcome:
    actual_fields: Mapping[str, JsonScalar] = {} if fields is None else fields
    return ExtractionOutcome(
        status="success",
        classification=classification,
        procedure_code=code,
        fields=actual_fields,
        evidence={field_id: f"evidence:{field_id}" for field_id in actual_fields},
        clarification_question=(
            "Câu hỏi tự do từ model không được dùng." if classification == "ambiguous" else None
        ),
        attempts=1,
    )


@dataclass(frozen=True, slots=True)
class ProcedureScenario:
    name: str
    code: str
    intro: str
    expected_field: str
    expected_value: JsonScalar
    short_answer: str
    other_field: str
    other_value: JsonScalar
    protected_field: str
    protected_value: JsonScalar
    conflicting_value: JsonScalar

    @property
    def question_id(self) -> str:
        return f"{self.code}:{self.expected_field}"


SCENARIOS = (
    pytest.param(
        ProcedureScenario(
            name="birth-copy",
            code="2.000635",
            intro="Tôi muốn xin bản sao Giấy khai sinh.",
            expected_field="requester_type",
            expected_value="self",
            short_answer="Cho bản thân tôi.",
            other_field="submission_channel",
            other_value="online",
            protected_field="copies_requested",
            protected_value=1,
            conflicting_value=3,
        ),
        id="birth-copy",
    ),
    pytest.param(
        ProcedureScenario(
            name="housing-confirmation",
            code="1.013314",
            intro="Tôi cần xác nhận diện tích nhà ở.",
            expected_field="requester_full_name",
            expected_value="Nguyễn Văn An",
            short_answer="Tên tôi là Nguyễn Văn An.",
            other_field="legal_dwelling_address",
            other_value="Số 10 phố Ví Dụ, Hà Nội",
            protected_field="land_area_m2",
            protected_value=80.0,
            conflicting_value=95.0,
        ),
        id="housing-confirmation",
    ),
    pytest.param(
        ProcedureScenario(
            name="temporary-residence",
            code="1.004194",
            intro="Tôi muốn đăng ký tạm trú.",
            expected_field="registration_mode",
            expected_value="individual_or_household",
            short_answer="Đăng ký cho cá nhân.",
            other_field="submission_channel",
            other_value="online",
            protected_field="submission_channel",
            protected_value="online",
            conflicting_value="direct",
        ),
        id="temporary-residence",
    ),
)


@pytest.fixture(scope="module")
def repository() -> ProcedureRepository:
    return ProcedureRepository.discover(ROOT)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_short_answer_receives_compact_context(
    repository: ProcedureRepository,
    scenario: ProcedureScenario,
) -> None:
    extractor = StubExtractor(
        outcome(scenario.code),
        outcome(
            scenario.code,
            fields={scenario.expected_field: scenario.expected_value},
        ),
    )
    session = ConversationSession(extractor, repository)

    first = session.send(scenario.intro)
    result = session.send(scenario.short_answer)

    assert first.next_action is NextAction.ASK_CLARIFICATION
    assert first.state.asked_question_ids == (scenario.question_id,)
    assert extractor.calls == [
        (scenario.intro, None),
        (
            scenario.short_answer,
            ExtractionTurnContext(scenario.code, scenario.expected_field),
        ),
    ]
    assert result.next_action is NextAction.CONFIRM_SUGGESTION
    assert result.extracted_fields == {scenario.expected_field: scenario.expected_value}
    assert result.suggestions[-1].field_id == scenario.expected_field
    assert result.state.asked_question_ids == (scenario.question_id,)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_unsupported_turn_preserves_context_without_reasking(
    repository: ProcedureRepository,
    scenario: ProcedureScenario,
) -> None:
    extractor = StubExtractor(
        outcome(scenario.code),
        outcome(None, classification="unsupported"),
    )
    session = ConversationSession(extractor, repository)

    first = session.send(scenario.intro)
    result = session.send("Bạn ăn cơm chưa?")

    assert result.next_action is NextAction.OUT_OF_SCOPE
    assert result.state.draft.procedure_code is not None
    assert result.state.draft.procedure_code.value == scenario.code
    assert result.state.asked_question_ids == (scenario.question_id,)
    assert first.reply not in result.reply
    assert "bạn có thể nhập mục" in result.reply.lower()
    assert scenario.expected_field not in result.reply
    assert extractor.calls[-1][1] == ExtractionTurnContext(
        scenario.code,
        scenario.expected_field,
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_ambiguous_turn_switches_previously_asked_field_to_manual_input(
    repository: ProcedureRepository,
    scenario: ProcedureScenario,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(scenario.code),
            outcome(None, classification="ambiguous"),
        ),
        repository,
    )

    first = session.send(scenario.intro)
    result = session.send("Tôi chưa rõ.")

    expected_action = (
        NextAction.ASK_CLARIFICATION if scenario.code == "2.000635" else NextAction.MANUAL_INPUT
    )
    assert result.next_action is expected_action
    assert result.state.asked_question_ids == (scenario.question_id,)
    assert first.reply not in result.reply
    expected_phrase = "ba lựa chọn" if scenario.code == "2.000635" else "bạn có thể nhập mục"
    assert expected_phrase in result.reply.lower()
    assert scenario.expected_field not in result.reply
    assert "Câu hỏi tự do từ model" not in result.reply


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_supported_empty_follow_up_does_not_repeat_question(
    repository: ProcedureRepository,
    scenario: ProcedureScenario,
) -> None:
    extractor = StubExtractor(outcome(scenario.code), outcome(scenario.code))
    session = ConversationSession(extractor, repository)

    first = session.send(scenario.intro)
    result = session.send("Vâng, tiếp tục đi.")

    assert result.next_action is NextAction.MANUAL_INPUT
    assert first.reply not in result.reply
    assert result.state.asked_question_ids == (scenario.question_id,)
    assert extractor.calls[-1][1] == ExtractionTurnContext(
        scenario.code,
        scenario.expected_field,
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_valid_other_field_becomes_suggestion_without_losing_expected_field(
    repository: ProcedureRepository,
    scenario: ProcedureScenario,
) -> None:
    extractor = StubExtractor(
        outcome(scenario.code),
        outcome(
            scenario.code,
            fields={scenario.other_field: scenario.other_value},
        ),
    )
    session = ConversationSession(extractor, repository)

    session.send(scenario.intro)
    result = session.send("Tôi bổ sung một thông tin khác trước.")

    assert result.next_action is NextAction.CONFIRM_SUGGESTION
    assert result.extracted_fields == {scenario.other_field: scenario.other_value}
    assert result.suggestions[-1].field_id == scenario.other_field
    assert result.suggestions[-1].suggested_value == scenario.other_value
    assert result.state.asked_question_ids == (scenario.question_id,)
    assert extractor.calls[-1][1] == ExtractionTurnContext(
        scenario.code,
        scenario.expected_field,
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_confirmed_value_is_not_overwritten_by_later_extraction(
    repository: ProcedureRepository,
    scenario: ProcedureScenario,
) -> None:
    extractor = StubExtractor(
        outcome(
            scenario.code,
            fields={scenario.protected_field: scenario.protected_value},
        ),
        outcome(
            scenario.code,
            fields={scenario.protected_field: scenario.conflicting_value},
        ),
    )
    session = ConversationSession(extractor, repository)

    proposed = session.send("Tôi cung cấp thông tin ban đầu.")
    confirmed = session.accept_suggestion(
        proposed.suggestions[-1].suggestion_id,
        expected_revision=proposed.state.draft.revision,
    )
    result = session.send("Model lại đề xuất một giá trị khác.")

    assert confirmed.state.asked_question_ids == (scenario.question_id,)
    assert result.draft[scenario.protected_field] == scenario.protected_value
    assert scenario.protected_field in result.state.draft.confirmed_fields
    assert scenario.protected_field not in result.state.draft.dirty_fields
    assert result.state.draft.revision == confirmed.state.draft.revision
    assert scenario.protected_field not in result.extracted_fields
    assert not any(
        suggestion.field_id == scenario.protected_field
        and suggestion.status is SuggestionStatus.PENDING
        for suggestion in result.suggestions
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_dirty_value_is_not_overwritten_by_later_extraction(
    repository: ProcedureRepository,
    scenario: ProcedureScenario,
) -> None:
    extractor = StubExtractor(
        outcome(scenario.code),
        outcome(
            scenario.code,
            fields={scenario.protected_field: scenario.conflicting_value},
        ),
    )
    session = ConversationSession(extractor, repository)

    selected = session.send(scenario.intro)
    edited = session.edit_field(
        scenario.protected_field,
        scenario.protected_value,
        expected_revision=selected.state.draft.revision,
    )
    result = session.send("Model lại đề xuất một giá trị khác.")

    assert edited.next_action is NextAction.MANUAL_INPUT
    assert result.draft[scenario.protected_field] == scenario.protected_value
    assert scenario.protected_field in result.state.draft.confirmed_fields
    assert scenario.protected_field in result.state.draft.dirty_fields
    assert result.state.draft.revision == edited.state.draft.revision
    assert scenario.protected_field not in result.extracted_fields
    assert not any(
        suggestion.field_id == scenario.protected_field
        and suggestion.status is SuggestionStatus.PENDING
        for suggestion in result.suggestions
    )
    assert extractor.calls[-1][1] == ExtractionTurnContext(
        scenario.code,
        scenario.expected_field,
    )


def test_close_clears_conversation_memory_and_blocks_reuse(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(StubExtractor(outcome("1.004194")), repository)
    session.send("Tôi muốn đăng ký tạm trú.")
    assert session.state.asked_question_ids == ("1.004194:registration_mode",)

    session.close()

    closed_state = session.state
    assert len(closed_state.asked_question_ids) == 0
    assert closed_state.messages == ()
    assert closed_state.turn_number == 0
    assert closed_state.draft.procedure_code is None
    with pytest.raises(RuntimeError, match="closed"):
        session.send("Không được xử lý tiếp.")
