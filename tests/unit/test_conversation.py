from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest

from vneguide.ai import ExtractionOutcome, ExtractionTurnContext, InformationRequest
from vneguide.core import ConversationSession, RevisionConflictError
from vneguide.data import ProcedureRepository
from vneguide.domain import NextAction, ProcedureCode, QATopic, SuggestionStatus

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
    reply: str | None = None,
    information_request: InformationRequest | None = None,
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
        reply=reply,
        error_code=error_code,
        information_request=information_request,
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
    session.initialize_procedure("2.000635")
    result = session.send("Tôi xin 2 bản trực tuyến")

    assert result.next_action is NextAction.CONFIRM_SUGGESTION
    assert result.draft == {}
    assert len(result.suggestions) == 2

    first, second = result.suggestions
    accepted = session.accept_suggestion(first.suggestion_id, expected_revision=0)
    assert accepted.draft[first.field_id] == first.suggested_value
    assert accepted.suggestions[0].status is SuggestionStatus.ACCEPTED
    assert accepted.state.messages[-1].content == accepted.reply

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
    assert edited.state.messages[-1].content == edited.reply


def test_reject_does_not_change_draft_and_caps_retries(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(outcome(fields={"copies_requested": 1})), repository
    )
    session.initialize_procedure("2.000635")
    result = session.send("Một bản")
    rejected = session.reject_suggestion(
        result.suggestions[0].suggestion_id,
        expected_revision=0,
    )
    assert rejected.draft == {}
    assert rejected.state.draft.revision == 1
    assert rejected.suggestions[0].status is SuggestionStatus.REJECTED
    assert rejected.state.messages[-1].content == rejected.reply


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
    session.initialize_procedure("2.000635")
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
    session.initialize_procedure("2.000635")
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
    assert edited.state.messages[-1].content == edited.reply
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
    session.initialize_procedure("2.000635")
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
    session.initialize_procedure("1.004194")

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
    session.initialize_procedure("2.000635")

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
    confirmed = session.send("Đúng")
    unsupported = session.send("Bạn ăn cơm chưa?")
    continued = session.send("Tôi đăng ký trực tuyến")

    assert initial.next_action is NextAction.CONFIRM_PROCEDURE
    assert confirmed.next_action is NextAction.ASK_CLARIFICATION
    assert "hình thức đăng ký" in confirmed.reply.lower()
    assert extractor.calls[0][1] is None
    for _, context in extractor.calls[1:]:
        assert context is not None
        assert context.active_procedure_code == "1.004194"
        assert context.expected_field_id == "registration_mode"
    assert unsupported.next_action is NextAction.OUT_OF_SCOPE
    assert "vẫn được giữ nguyên" in unsupported.reply
    assert "hình thức đăng ký" in unsupported.reply.lower()
    assert "registration_mode" not in unsupported.reply
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
    session.send("Đúng")

    result = session.send("Tôi chưa rõ")
    manual = session.send("Vẫn chưa rõ")

    assert result.next_action is NextAction.MANUAL_INPUT
    assert "hình thức đăng ký" in result.reply.lower()
    assert "Bạn muốn làm thủ tục nào?" not in result.reply
    assert extractor.calls[-1][1] == ExtractionTurnContext(
        active_procedure_code="1.004194",
        expected_field_id="registration_mode",
    )
    assert manual.next_action is NextAction.MANUAL_INPUT
    assert "hình thức đăng ký" in manual.reply.lower()
    assert "registration_mode" not in manual.reply


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
    session.send("Đúng")
    relationship = session.send("Cho con tôi")
    channel = session.send("Đăng ký trực tuyến")

    assert relationship.next_action is NextAction.MANUAL_INPUT
    assert "loại người yêu cầu" in relationship.reply.lower()
    assert "requester_type" not in relationship.reply
    assert relationship.state.draft.procedure_code is not None
    assert relationship.state.draft.procedure_code.value == "2.000635"
    assert channel.next_action is NextAction.CONFIRM_SUGGESTION
    assert channel.suggestions[-1].field_id == "submission_channel"
    accepted = session.accept_suggestion(
        channel.suggestions[-1].suggestion_id,
        expected_revision=0,
    )
    assert accepted.next_action is NextAction.MANUAL_INPUT
    assert "loại người yêu cầu" in accepted.reply.lower()
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
    session.send("Đúng")
    result = session.send("Tôi muốn đăng ký tạm trú")
    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert result.state.draft.procedure_code is not None
    assert result.state.draft.procedure_code.value == "2.000635"


def test_unscoped_intent_requires_confirmation_without_mutating_draft(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(
            procedure_code="1.004194",
            fields={"submission_channel": "online"},
            evidence={"submission_channel": "trực tuyến"},
            reply="Dạ, em đã hiểu yêu cầu của anh/chị ạ.",
        )
    )
    session = ConversationSession(extractor, repository)

    result = session.send("Tôi muốn đăng ký tạm trú trực tuyến")

    assert result.next_action is NextAction.CONFIRM_PROCEDURE
    assert result.state.pending_procedure_code is not None
    assert result.state.pending_procedure_code.value == "1.004194"
    assert result.state.draft.procedure_code is None
    assert result.state.draft.revision == 0
    assert result.draft == {}
    assert result.suggestions == ()
    assert result.extracted_fields == {}
    assert result.state.asked_question_ids == ()
    assert result.state.messages[-1].content == result.reply


def test_affirmative_confirmation_activates_without_calling_extractor_again(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(outcome(procedure_code="1.004194"))
    session = ConversationSession(extractor, repository)
    session.send("Tôi muốn đăng ký tạm trú")

    result = session.send("Dạ, đúng rồi ạ")

    assert len(extractor.calls) == 1
    assert result.state.pending_procedure_code is None
    assert result.state.draft.procedure_code is not None
    assert result.state.draft.procedure_code.value == "1.004194"
    assert result.state.draft.pack_version is not None
    assert result.state.draft.revision == 0
    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "hình thức đăng ký" in result.reply.lower()
    assert "cá nhân hoặc hộ gia đình" in result.reply
    assert "theo danh sách" in result.reply
    assert "đơn vị lực lượng vũ trang" in result.reply


def test_confirmation_utterance_keeps_fields_extracted_in_the_same_turn(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(procedure_code="1.004194"),
        outcome(
            procedure_code="1.004194",
            fields={"submission_channel": "online"},
            evidence={"submission_channel": "trực tuyến"},
        ),
    )
    session = ConversationSession(extractor, repository)
    session.send("Tôi muốn đăng ký tạm trú")

    result = session.send("Đúng, tôi nộp trực tuyến")

    assert len(extractor.calls) == 2
    assert extractor.calls[1][1] == ExtractionTurnContext(
        active_procedure_code="1.004194",
        expected_field_id=None,
        confirmation_required=True,
    )
    assert result.state.pending_procedure_code is None
    assert result.state.draft.procedure_code is not None
    assert result.state.draft.procedure_code.value == "1.004194"
    assert result.next_action is NextAction.CONFIRM_SUGGESTION
    assert result.extracted_fields == {"submission_channel": "online"}
    assert len(result.suggestions) == 1
    assert result.suggestions[0].field_id == "submission_channel"


def test_housing_confirmation_uses_a_short_procedure_label(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(StubExtractor(outcome(procedure_code="1.013314")), repository)

    result = session.send("Tôi cần xác nhận nhà ở để đăng ký thường trú")

    assert result.next_action is NextAction.CONFIRM_PROCEDURE
    assert "xác nhận điều kiện nhà ở để đăng ký thường trú" in result.reply
    assert "thuê, mượn, ở nhờ" not in result.reply
    assert len(result.reply) < 180


def test_negative_confirmation_clears_pending_choice(repository: ProcedureRepository) -> None:
    extractor = StubExtractor(outcome(procedure_code="2.000635"))
    session = ConversationSession(extractor, repository)
    session.send("Tôi cần bản sao Giấy khai sinh")

    result = session.send("Không phải ạ")

    assert len(extractor.calls) == 1
    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert result.state.pending_procedure_code is None
    assert result.state.draft.procedure_code is None
    assert result.state.draft.revision == 0


def test_explicit_new_intent_replaces_pending_choice(repository: ProcedureRepository) -> None:
    extractor = StubExtractor(
        outcome(procedure_code="2.000635"),
        outcome(procedure_code="1.004194"),
    )
    session = ConversationSession(extractor, repository)
    first = session.send("Tôi cần bản sao Giấy khai sinh")
    changed = session.send("Thực ra tôi muốn đăng ký tạm trú")

    assert first.state.pending_procedure_code is not None
    assert first.state.pending_procedure_code.value == "2.000635"
    assert changed.next_action is NextAction.CONFIRM_PROCEDURE
    assert changed.state.pending_procedure_code is not None
    assert changed.state.pending_procedure_code.value == "1.004194"
    assert changed.state.draft.procedure_code is None
    assert [context for _, context in extractor.calls] == [
        None,
        ExtractionTurnContext("2.000635", confirmation_required=True),
    ]


@pytest.mark.parametrize(
    ("message", "second_outcome", "expected_action", "expected_pending"),
    [
        (
            "Vâng nhưng không phải thủ tục này",
            outcome(classification="ambiguous", procedure_code=None),
            NextAction.ASK_CLARIFICATION,
            None,
        ),
        (
            "Đúng không ạ, tôi đang hỏi lại",
            outcome(classification="ambiguous", procedure_code=None),
            NextAction.CONFIRM_PROCEDURE,
            "2.000635",
        ),
        (
            "OK nhưng tôi muốn đăng ký tạm trú",
            outcome(procedure_code="1.004194"),
            NextAction.CONFIRM_PROCEDURE,
            "1.004194",
        ),
        (
            "Không, tôi muốn đăng ký tạm trú",
            outcome(procedure_code="1.004194"),
            NextAction.CONFIRM_PROCEDURE,
            "1.004194",
        ),
        (
            "Vâng nhưng không phải thủ tục này",
            outcome(procedure_code="2.000635"),
            NextAction.ASK_CLARIFICATION,
            None,
        ),
    ],
)
def test_pending_confirmation_handles_rejection_doubt_and_new_intent(
    repository: ProcedureRepository,
    message: str,
    second_outcome: ExtractionOutcome,
    expected_action: NextAction,
    expected_pending: str | None,
) -> None:
    extractor = StubExtractor(outcome(procedure_code="2.000635"), second_outcome)
    session = ConversationSession(extractor, repository)
    session.send("Tôi cần bản sao Giấy khai sinh")

    result = session.send(message)

    assert result.next_action is expected_action
    assert result.state.draft.procedure_code is None
    assert (
        result.state.pending_procedure_code.value
        if result.state.pending_procedure_code is not None
        else None
    ) == expected_pending
    assert extractor.calls[1][1] == ExtractionTurnContext(
        "2.000635",
        confirmation_required=True,
    )


@pytest.mark.parametrize(
    "message",
    [
        "Đúng thủ tục rồi, nhưng địa chỉ này không đúng",
        "Đúng, nhưng không phải cho tôi mà cho con tôi",
        "Không phải thủ tục khác, đúng thủ tục này",
        "Tôi không muốn làm thủ tục khác, đúng thủ tục này",
        "Tôi không muốn chuyển sang thủ tục khác, đúng thủ tục này",
        "Tôi không hề muốn một thủ tục khác, đúng thủ tục này",
        "Tôi đâu có muốn thủ tục khác, đúng thủ tục này",
        "Không sai thủ tục, đúng thủ tục này",
        "Không nhầm thủ tục, đúng thủ tục này",
        "Không đúng thủ tục khác, đúng thủ tục này",
    ],
)
def test_field_correction_language_does_not_reject_the_pending_procedure(
    repository: ProcedureRepository,
    message: str,
) -> None:
    extractor = StubExtractor(
        outcome(procedure_code="2.000635"),
        outcome(procedure_code="2.000635"),
    )
    session = ConversationSession(extractor, repository)
    session.send("Tôi cần bản sao Giấy khai sinh")

    result = session.send(message)

    assert result.state.pending_procedure_code is None
    assert result.state.draft.procedure_code is not None
    assert result.state.draft.procedure_code.value == "2.000635"


@pytest.mark.parametrize(
    "message",
    [
        "Vâng nhưng không phải thủ tục này",
        "Tôi không muốn làm thủ tục này nữa",
    ],
)
def test_explicit_procedure_rejection_clears_pending_even_if_provider_fails(
    repository: ProcedureRepository,
    message: str,
) -> None:
    extractor = StubExtractor(
        outcome(procedure_code="2.000635"),
        outcome(status="fallback", procedure_code=None, error_code="provider_timeout"),
    )
    session = ConversationSession(extractor, repository)
    session.send("Tôi cần bản sao Giấy khai sinh")

    result = session.send(message)

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert result.state.pending_procedure_code is None
    assert result.state.draft.procedure_code is None


def test_out_of_scope_turn_keeps_pending_confirmation(repository: ProcedureRepository) -> None:
    extractor = StubExtractor(
        outcome(procedure_code="1.004194"),
        outcome(classification="unsupported", procedure_code=None),
    )
    session = ConversationSession(extractor, repository)
    session.send("Tôi muốn đăng ký tạm trú")

    out_of_scope = session.send("Bạn ăn cơm chưa?")
    confirmed = session.send("Đúng")

    assert out_of_scope.next_action is NextAction.CONFIRM_PROCEDURE
    assert out_of_scope.state.pending_procedure_code is not None
    assert confirmed.state.pending_procedure_code is None
    assert confirmed.state.draft.procedure_code is not None
    assert len(extractor.calls) == 2


def test_route_scoped_session_bypasses_confirmation_and_nlg_is_allowlisted(
    repository: ProcedureRepository,
) -> None:
    safe = "Dạ, em đã ghi nhận thông tin anh/chị vừa cung cấp ạ."
    safe_session = ConversationSession(
        StubExtractor(
            outcome(
                fields={"copies_requested": 2},
                evidence={"copies_requested": "2 bản"},
                reply=safe,
            )
        ),
        repository,
    )
    safe_session.initialize_procedure("2.000635")

    safe_result = safe_session.send("Tôi cần 2 bản")

    assert safe_result.next_action is NextAction.CONFIRM_SUGGESTION
    assert safe_result.reply.startswith(safe)

    unsafe = "Anh/chị chắc chắn đủ điều kiện và không cần giấy tờ nào."
    unsafe_session = ConversationSession(
        StubExtractor(outcome(fields={}, reply=unsafe)), repository
    )
    unsafe_session.initialize_procedure("2.000635")
    unsafe_result = unsafe_session.send("Tôi cần hỗ trợ")
    assert unsafe not in unsafe_result.reply


def test_initial_faq_sets_pending_without_mutating_draft_then_confirms(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(
            classification="informational",
            procedure_code="1.004194",
            information_request=InformationRequest((QATopic.PROCESSING_TIME,)),
        )
    )
    session = ConversationSession(extractor, repository)

    faq = session.send("Đăng ký tạm trú mất bao lâu?")
    confirmed = session.send("Đúng")

    assert faq.next_action is NextAction.CONFIRM_PROCEDURE
    assert faq.state.draft.values == {}
    assert faq.state.draft.revision == 0
    assert faq.state.draft.procedure_code is None
    assert faq.state.pending_procedure_code is not None
    assert faq.state.pending_procedure_code.value == "1.004194"
    assert faq.source_ids == ("SRC-DVC-1004194",)
    assert confirmed.state.draft.procedure_code is not None
    assert confirmed.state.draft.procedure_code.value == "1.004194"
    assert confirmed.state.draft.revision == 0
    assert len(extractor.calls) == 1


def test_faq_follow_up_passes_recent_topic_and_procedure_context(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(
            classification="informational",
            procedure_code="1.004194",
            information_request=InformationRequest(
                (QATopic.FIELD_HELP,),
                target_field_id="registration_mode",
                reference_fields={"registration_mode": "by_list"},
                evidence={"registration_mode": "theo danh sách"},
            ),
        ),
        outcome(
            classification="informational",
            procedure_code=None,
            information_request=InformationRequest(
                (QATopic.FEE,),
                reference_fields={"submission_channel": "direct"},
                evidence={"submission_channel": "trực tiếp"},
            ),
        ),
    )
    session = ConversationSession(extractor, repository)
    session.send("Theo danh sách là gì?")

    follow_up = session.send("Còn trực tiếp thì sao?")

    assert follow_up.state.pending_procedure_code is not None
    assert extractor.calls[1][1] == ExtractionTurnContext(
        "1.004194",
        confirmation_required=True,
        recent_information_topics=(QATopic.FIELD_HELP,),
        recent_information_procedure_code="1.004194",
    )
    assert follow_up.state.recent_information_topics == (QATopic.FEE,)


def test_active_procedure_scopes_informational_outcome_without_code(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(
                classification="informational",
                procedure_code=None,
                information_request=InformationRequest((QATopic.FEE,)),
            )
        ),
        repository,
    )
    session.initialize_procedure("1.013314")

    faq = session.send("Thủ tục này có mất phí không?")

    assert faq.state.draft.procedure_code is ProcedureCode.HOUSING_CONDITION_CONFIRMATION
    assert faq.next_action is NextAction.ASK_CLARIFICATION
    assert "không thu phí" in faq.reply
    assert faq.source_ids == ("SRC-DVC-1013314",)


def test_successful_faq_clears_only_provider_failure_counter(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(status="fallback", procedure_code=None, error_code="provider_timeout"),
            outcome(
                classification="informational",
                procedure_code=None,
                information_request=InformationRequest((QATopic.FEE,)),
            ),
            outcome(status="fallback", procedure_code=None, error_code="provider_timeout"),
        ),
        repository,
    )
    session.initialize_procedure("1.013314")
    first_failure = session.send("Tôi cần hỗ trợ")
    faq = session.send("Có mất phí không?")

    second_failure = session.send("Tôi tiếp tục khai")

    assert first_failure.next_action is NextAction.RETRY
    assert "__extractor__" not in faq.state.clarification_attempts
    assert second_failure.next_action is NextAction.RETRY


def test_supported_intent_clears_stale_qa_context_when_pending_changes(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(
            classification="informational",
            procedure_code="2.000635",
            information_request=InformationRequest((QATopic.FEE,)),
        ),
        outcome(procedure_code="1.004194"),
        outcome(classification="ambiguous", procedure_code=None),
    )
    session = ConversationSession(extractor, repository)
    session.send("Bản sao giấy khai sinh mất phí bao nhiêu?")

    changed = session.send("Thực ra tôi muốn đăng ký tạm trú")
    session.send("Tôi chưa chắc")

    assert changed.state.pending_procedure_code is ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION
    assert changed.state.recent_information_procedure_code is None
    assert changed.state.recent_information_topics == ()
    assert extractor.calls[2][1] == ExtractionTurnContext(
        "1.004194",
        confirmation_required=True,
    )


def test_faq_preserves_active_suggestion_and_form_state(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(
            procedure_code="1.004194",
            fields={"registration_mode": "individual_or_household"},
            evidence={"registration_mode": "cá nhân"},
        ),
        outcome(
            classification="informational",
            procedure_code="1.004194",
            information_request=InformationRequest((QATopic.FEE,)),
        ),
    )
    session = ConversationSession(extractor, repository)
    session.initialize_procedure("1.004194")
    first = session.send("Tôi đăng ký theo cá nhân")
    draft_before = first.state.draft
    suggestions_before = first.state.suggestions
    attempts_before = first.state.clarification_attempts
    questions_before = first.state.asked_question_ids

    faq = session.send("Lệ phí là bao nhiêu?")

    assert faq.next_action is NextAction.CONFIRM_SUGGESTION
    assert faq.state.draft == draft_before
    assert faq.state.suggestions == suggestions_before
    assert faq.state.clarification_attempts == attempts_before
    assert faq.state.asked_question_ids == questions_before
    assert "7.000 đồng" in faq.reply


def test_faq_repeats_current_question_without_marking_another_attempt(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(procedure_code="1.004194", fields={}),
        outcome(
            classification="informational",
            procedure_code="1.004194",
            information_request=InformationRequest(
                (QATopic.FIELD_HELP,),
                target_field_id="registration_mode",
                reference_fields={"registration_mode": "by_list"},
                evidence={"registration_mode": "theo danh sách"},
            ),
        ),
    )
    session = ConversationSession(extractor, repository)
    session.initialize_procedure("1.004194")
    first = session.send("Tôi cần hỗ trợ")

    faq = session.send("Theo danh sách tức là gì?")

    assert first.next_action is NextAction.ASK_CLARIFICATION
    assert faq.next_action is NextAction.ASK_CLARIFICATION
    assert faq.state.asked_question_ids == first.state.asked_question_ids
    assert faq.state.clarification_attempts == first.state.clarification_attempts
    assert "Tờ khai CT01 của từng người" in faq.reply
    assert "Anh/chị chọn hình thức đăng ký" in faq.reply


def test_cross_procedure_faq_is_reference_only_for_active_form(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(
            classification="informational",
            procedure_code="1.004194",
            information_request=InformationRequest((QATopic.FEE,)),
        )
    )
    session = ConversationSession(extractor, repository)
    session.initialize_procedure("2.000635")

    faq = session.send("Đăng ký tạm trú mất bao nhiêu tiền?")

    assert faq.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert faq.state.draft.revision == 0
    assert faq.state.pending_procedure_code is None
    assert "Thông tin trên chỉ để tham khảo" in faq.reply
    assert "đặt lại phiên" in faq.reply
    assert set(faq.source_ids) == {"SRC-DVC-1004194", "SRC-FEE-75-2022"}


def test_unscoped_faq_asks_for_procedure_without_recording_qa_memory(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(
                classification="informational",
                procedure_code=None,
                information_request=InformationRequest((QATopic.FEE,)),
            )
        ),
        repository,
    )

    result = session.send("Phí bao nhiêu?")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert result.source_ids == ()
    assert result.state.draft.revision == 0
    assert result.state.recent_information_procedure_code is None
    assert result.state.recent_information_topics == ()


def test_rejecting_faq_pending_procedure_clears_qa_memory(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(
                classification="informational",
                procedure_code="2.000635",
                information_request=InformationRequest((QATopic.DOCUMENTS,)),
            )
        ),
        repository,
    )
    session.send("Xin bản sao khai sinh cần giấy tờ gì?")

    rejected = session.send("Không phải")

    assert rejected.state.pending_procedure_code is None
    assert rejected.state.recent_information_procedure_code is None
    assert rejected.state.recent_information_topics == ()


def test_reset_after_active_faq_clears_dirty_draft_and_qa_memory(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(
                classification="informational",
                procedure_code="1.004194",
                information_request=InformationRequest((QATopic.CHANNELS,)),
            )
        ),
        repository,
    )
    session.initialize_procedure("1.004194")
    session.edit_field("submission_channel", "online", expected_revision=0)

    faq = session.send("Có những kênh nộp nào?")
    session.close()

    assert faq.state.draft.revision == 1
    assert faq.state.draft.dirty_fields == {"submission_channel"}
    assert session.state.draft.revision == 0
    assert session.state.draft.values == {}
    assert session.state.recent_information_procedure_code is None
    assert session.state.recent_information_topics == ()


def test_close_clears_state_and_prevents_reuse(repository: ProcedureRepository) -> None:
    session = ConversationSession(StubExtractor(), repository)
    session.close()
    assert session.state.turn_number == 0
    with pytest.raises(RuntimeError, match="closed"):
        session.send("không được xử lý")
