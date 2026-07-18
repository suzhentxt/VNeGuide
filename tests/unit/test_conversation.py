from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest

from vneguide.ai import ExtractionOutcome, ExtractionTurnContext
from vneguide.core import ConversationSession, RevisionConflictError
from vneguide.data import ProcedureRepository
from vneguide.domain import NextAction, ProcedureCode, SuggestionStatus

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
    clarification_question: str | None = None,
) -> ExtractionOutcome:
    return ExtractionOutcome(
        status=status,
        classification=classification if status == "success" else None,
        procedure_code=procedure_code if status == "success" else None,
        fields={} if fields is None else fields,  # type: ignore[arg-type]
        evidence={} if evidence is None else evidence,
        clarification_question=(
            clarification_question
            if clarification_question is not None
            else "Bạn muốn làm thủ tục nào?"
            if classification == "ambiguous"
            else None
        ),
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
    session.initialize_procedure("2.000635")
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


def test_incomplete_draft_is_never_reported_ready_to_submit(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(outcome(procedure_code="1.004194")),
        repository,
    )

    result = session.send("Tôi muốn đăng ký tạm trú")

    assert result.missing_fields
    assert result.validation is not None
    assert result.validation.status.value == "needs_correction"
    assert result.validation.readiness_score is None
    assert result.next_action is NextAction.ASK_CLARIFICATION


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


def test_uncertain_birth_request_keeps_safe_plain_language_choices(
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
    session.accept_suggestion(
        initial.suggestions[0].suggestion_id,
        expected_revision=0,
    )
    result = session.send("Tôi chưa rõ")
    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "ba lựa chọn" in result.reply
    assert "requester_type" not in result.reply


def test_guided_form_help_skips_extractor_and_asks_the_next_reviewed_field(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor()
    session = ConversationSession(extractor, repository)
    session.initialize_procedure("1.004194")

    result = session.send("Hãy hướng dẫn tôi điền hồ sơ từng bước.")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "hỏi từng mục" in result.reply
    assert "hình thức đăng ký" in result.reply.lower()
    assert extractor.calls == []


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
    assert "đúng không" in initial.reply.lower()
    assert extractor.calls[0][1] is None
    for _, context in extractor.calls[1:]:
        assert context is not None
        assert context.active_procedure_code == "1.004194"
        assert context.expected_field_id == "registration_mode"
    assert unsupported.next_action is NextAction.ASK_CLARIFICATION
    assert "ngoài" not in unsupported.reply.lower()
    assert "vẫn đang cùng bạn" in unsupported.reply
    assert "hình thức đăng ký" in unsupported.reply.lower()
    assert "registration_mode" not in unsupported.reply
    assert continued.next_action is NextAction.CONFIRM_SUGGESTION
    assert continued.suggestions[-1].field_id == "submission_channel"


def test_generic_birth_certificate_request_is_clarified_before_extraction(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor()
    session = ConversationSession(extractor, repository)
    session.initialize_procedure("1.004194")

    result = session.send("tôi muốn làm giấy khai sinh")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "bản sao Giấy khai sinh" in result.reply
    assert "đăng ký khai sinh mới" in result.reply
    assert "ngoài ba thủ tục" not in result.reply
    assert "Đăng ký tạm trú" in result.reply
    assert result.state.draft.procedure_code is not None
    assert result.state.draft.procedure_code.value == "1.004194"
    assert result.draft == {}
    assert extractor.calls == []


def test_dialect_birth_request_is_normalized_before_scope_clarification(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor()
    session = ConversationSession(extractor, repository)

    result = session.send("tui ưng mần giấy khai sinh")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "bản sao Giấy khai sinh" in result.reply
    assert "đăng ký khai sinh mới" in result.reply
    assert result.state.draft.procedure_code is None
    assert extractor.calls == []


def test_birth_clarification_can_switch_to_residence_services(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor()
    session = ConversationSession(extractor, repository)

    birth = session.send("tôi muốn làm giấy khai sinh")
    housing = session.send("thường trú")
    temporary = session.send("đổi thành đăng kí tạm trú")

    assert "đăng ký khai sinh mới" in birth.reply
    assert housing.state.draft.procedure_code is ProcedureCode.HOUSING_CONDITION_CONFIRMATION
    assert "xác nhận Mẫu số 02" in housing.reply
    assert temporary.state.draft.procedure_code is ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION
    assert "đã chuyển sang yêu cầu mới" in temporary.reply
    assert "đăng ký tạm trú" in temporary.reply
    assert temporary.state.draft.revision == 1
    assert extractor.calls == []


def test_birth_scope_clarification_remembers_copy_choice_and_child_context(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(
            procedure_code="2.000635",
            fields={"requester_type": "authorized_person"},
            evidence={"requester_type": "người được ủy quyền"},
        )
    )
    session = ConversationSession(extractor, repository)

    ambiguous = session.send("tôi muốn làm giấy khai sinh")
    selected = session.send("tôi muốn xin bản sao")
    child = session.send("cho con tôi")
    role = session.send("Tôi là người được ủy quyền")

    assert ambiguous.next_action is NextAction.ASK_CLARIFICATION
    assert selected.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert "bản thân" in selected.reply
    assert child.next_action is NextAction.ASK_CLARIFICATION
    assert "đã ghi nhận" in child.reply.lower()
    assert "cho con" in child.reply.lower()
    assert "requester_type" not in child.reply
    assert role.next_action is NextAction.CONFIRM_SUGGESTION
    assert role.suggestions[-1].field_id == "requester_type"
    assert extractor.calls == [
        (
            "Tôi là người được ủy quyền",
            ExtractionTurnContext("2.000635", "requester_type"),
        )
    ]


def test_birth_copy_typo_selects_supported_procedure_without_model(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor()
    session = ConversationSession(extractor, repository)

    result = session.send("tôi muốn xin bảo sao giấy khai sinh")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert result.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert "bản thân" in result.reply
    assert extractor.calls == []


def test_uncertain_birth_requester_keeps_plain_language_choices(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(outcome(procedure_code="2.000635", fields={})),
        repository,
    )
    session.send("Tôi muốn xin bản sao Giấy khai sinh")

    result = session.send("Tôi chưa rõ")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "ba lựa chọn" in result.reply
    assert "tự điền" in result.reply
    assert "requester_type" not in result.reply


@pytest.mark.parametrize(
    "message",
    [
        "Tôi muốn xin bản sao Giấy khai sinh",
        "Tôi cần đăng ký khai sinh cho con mới sinh",
    ],
)
def test_explicit_birth_requests_still_reach_extraction(
    repository: ProcedureRepository,
    message: str,
) -> None:
    extractor = StubExtractor(outcome(classification="unsupported", procedure_code=None))
    session = ConversationSession(extractor, repository)

    session.send(message)

    assert extractor.calls == [(message, None)]


@pytest.mark.parametrize(
    ("message", "classification", "expected_code"),
    [
        ("tôi muốn làm bản sao giấy khai sinh", "ambiguous", "2.000635"),
        ("tôi muốn cấp bản sao Giấy khai sinh", "unsupported", "2.000635"),
        ("Tôi muốn đăng ký tạm trú", "unsupported", "1.004194"),
        ("Tôi cần xin xác nhận diện tích nhà ở", "ambiguous", "1.013314"),
        ("Tôi muốn đăng ký thường trú", "ambiguous", "1.013314"),
        (
            "Tôi muốn xác nhận diện tích nhà ở để đăng ký thường trú",
            "unsupported",
            "1.013314",
        ),
    ],
)
def test_reviewed_alias_rescues_incorrect_model_routing(
    repository: ProcedureRepository,
    message: str,
    classification: str,
    expected_code: str,
) -> None:
    extractor = StubExtractor(
        outcome(classification=classification, procedure_code=None),
    )
    session = ConversationSession(extractor, repository)

    result = session.send(message)

    assert result.state.draft.procedure_code is ProcedureCode(expected_code)
    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "ngoài ba thủ tục" not in result.reply.lower()
    assert extractor.calls == [(message, None)]


def test_permanent_residence_shorthand_keeps_housing_confirmation_context(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(classification="ambiguous", procedure_code=None),
        outcome(classification="ambiguous", procedure_code=None),
    )
    session = ConversationSession(extractor, repository)

    first = session.send("tôi muốn đăng ký thường trú")
    clarified = session.send("tôi muốn xác nhận diện tích nhà ở để đăng ký thường trú")

    assert first.state.draft.procedure_code is ProcedureCode.HOUSING_CONDITION_CONFIRMATION
    assert clarified.state.draft.procedure_code is ProcedureCode.HOUSING_CONDITION_CONFIRMATION
    assert first.next_action is NextAction.ASK_CLARIFICATION
    assert clarified.next_action is NextAction.ASK_CLARIFICATION
    assert "Bạn cần hỗ trợ đăng ký tạm trú" not in first.reply
    assert "Bạn cần hỗ trợ đăng ký tạm trú" not in clarified.reply
    assert "ngoài ba thủ tục" not in first.reply.lower()
    assert "ngoài ba thủ tục" not in clarified.reply.lower()


def test_permanent_residence_clarification_confirms_service_before_asking_fields(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(classification="ambiguous", procedure_code=None),
        outcome(classification="ambiguous", procedure_code=None),
    )
    session = ConversationSession(extractor, repository)

    unclear = session.send("tôi muốn xin giấy tờ thường trú")
    selected = session.send("tôi muốn đăng ký thường trú")

    assert unclear.state.draft.procedure_code is None
    assert unclear.reply == "Bạn muốn làm thủ tục nào?"
    assert selected.state.draft.procedure_code is ProcedureCode.HOUSING_CONDITION_CONFIRMATION
    assert selected.next_action is NextAction.ASK_CLARIFICATION
    assert "xác nhận Mẫu số 02" in selected.reply
    assert "Họ tên người đề nghị" not in selected.reply
    assert selected.suggestions == ()
    assert extractor.calls == [
        ("tôi muốn xin giấy tờ thường trú", None),
        ("tôi muốn đăng ký thường trú", None),
    ]


def test_birth_copy_confirmation_never_falls_out_of_scope_after_ambiguous_turn(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        outcome(classification="ambiguous", procedure_code=None),
        outcome(classification="unsupported", procedure_code=None),
    )
    session = ConversationSession(extractor, repository)

    first = session.send("tôi muốn làm bản sao giấy khai sinh")
    confirmed = session.send("tôi muốn cấp bản sao Giấy khai sinh")

    assert first.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert confirmed.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert confirmed.next_action is NextAction.ASK_CLARIFICATION
    assert "ngoài ba thủ tục" not in confirmed.reply.lower()


def test_first_service_turn_keeps_extracted_field_as_pending_memory(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(
                procedure_code="2.000635",
                fields={"requester_type": "self"},
                evidence={"requester_type": "cho tôi"},
            )
        ),
        repository,
    )

    result = session.send("tôi muốn xin bản sao giấy khai sinh cho tôi")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert result.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert len(result.suggestions) == 1
    assert result.suggestions[0].field_id == "requester_type"
    assert result.suggestions[0].suggested_value == "self"
    assert result.draft == {}


def test_reviewed_service_still_reaches_confirmation_when_provider_fails(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(outcome(status="fallback", error_code="provider_error")),
        repository,
    )

    result = session.send("tôi muốn xin bản sao giấy khai sinh cho tôi")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert result.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert "ngoài ba thủ tục" not in result.reply.lower()
    assert "bạn đang cần bản sao" in result.reply.lower()
    assert result.suggestions == ()


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

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "hình thức đăng ký" in result.reply.lower()
    assert "registration_mode" not in result.reply
    assert "Bạn muốn làm thủ tục nào?" not in result.reply
    assert extractor.calls[-1][1] == ExtractionTurnContext(
        active_procedure_code="1.004194",
        expected_field_id="registration_mode",
    )
    assert manual.next_action is NextAction.ASK_CLARIFICATION
    assert "hình thức đăng ký" in manual.reply.lower()


def test_supported_empty_extraction_uses_natural_model_clarification(
    repository: ProcedureRepository,
) -> None:
    question = (
        "Tôi hiểu bạn đang tiếp tục hồ sơ tạm trú. "
        "Bạn muốn đăng ký cho cá nhân, hộ gia đình hay theo danh sách?"
    )
    session = ConversationSession(
        StubExtractor(
            outcome(
                procedure_code="1.004194",
                clarification_question=question,
            )
        ),
        repository,
    )
    session.initialize_procedure("1.004194")

    result = session.send("Tôi chưa biết nói thế nào")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert result.reply == question
    assert result.suggestions == ()


def test_birth_copy_follow_ups_keep_the_active_procedure_without_inference(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
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

    assert relationship.next_action is NextAction.ASK_CLARIFICATION
    assert "đã ghi nhận" in relationship.reply.lower()
    assert "cho con" in relationship.reply.lower()
    assert "requester_type" not in relationship.reply
    assert relationship.state.draft.procedure_code is not None
    assert relationship.state.draft.procedure_code.value == "2.000635"
    assert channel.next_action is NextAction.CONFIRM_SUGGESTION
    assert channel.suggestions[-1].field_id == "submission_channel"
    accepted = session.accept_suggestion(
        channel.suggestions[-1].suggestion_id,
        expected_revision=0,
    )
    assert accepted.next_action is NextAction.ASK_CLARIFICATION
    assert "người được ủy quyền" in accepted.reply.lower()
    assert "requester_type" not in accepted.reply
    assert [call[1] for call in extractor.calls] == [
        None,
        ExtractionTurnContext("2.000635", "requester_type"),
    ]


def test_greeting_is_not_presented_as_an_out_of_scope_service(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor()
    session = ConversationSession(extractor, repository)

    result = session.send("Xin chào")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "xin chào" in result.reply.lower()
    assert "ngoài" not in result.reply.lower()
    assert extractor.calls == []


def test_typo_guidance_request_explains_the_current_field_without_model(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor()
    session = ConversationSession(extractor, repository)
    session.initialize_procedure("2.000635")
    session.edit_field("requester_type", "authorized_person", expected_revision=0)
    session.edit_field("requester_full_name", "Nguyễn Văn A", expected_revision=1)
    session.edit_field("requester_personal_id", "000000000001", expected_revision=2)

    result = session.send("hướng dẫn tôi điền nôis đi")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "họ tên người có sự kiện khai sinh" in result.reply.lower()
    assert "nhập đầy đủ họ và tên" in result.reply.lower()
    assert "ngoài" not in result.reply.lower()
    assert extractor.calls == []


def test_natural_new_intent_switches_procedure_and_requires_confirmation(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(fields={"copies_requested": 1}),
        ),
        repository,
    )
    session.send("Xin một bản")
    result = session.send("Tôi muốn đăng ký tạm trú")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert result.state.draft.procedure_code is ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION
    assert "đã chuyển sang yêu cầu mới" in result.reply
    assert "đúng không" in result.reply


def test_colloquial_change_of_mind_switches_without_command_phrase(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(outcome(procedure_code="2.000635"))
    session = ConversationSession(extractor, repository)

    birth_scope = session.send("tui ưng mần giấy khai sinh")
    birth_copy = session.send("tui ưng xin bản sao giấy khai sinh")
    temporary = session.send("thôi tui ưng đăng kí tạm trú")

    assert "đăng ký khai sinh mới" in birth_scope.reply
    assert birth_copy.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert temporary.state.draft.procedure_code is ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION
    assert temporary.next_action is NextAction.ASK_CLARIFICATION
    assert "đã chuyển sang yêu cầu mới" in temporary.reply
    assert "đăng ký tạm trú" in temporary.reply
    assert extractor.calls == []


def test_merely_comparing_another_service_does_not_discard_active_draft(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(procedure_code="2.000635"),
            outcome(procedure_code="1.004194"),
        ),
        repository,
    )
    session.send("Tôi xin bản sao Giấy khai sinh")

    result = session.send("Đăng ký tạm trú khác gì thủ tục này?")

    assert result.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert "bạn có muốn chuyển" in result.reply.lower()


def test_information_question_with_want_phrase_does_not_switch_automatically(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(procedure_code="2.000635"),
            outcome(procedure_code="1.004194"),
        ),
        repository,
    )
    session.send("Tôi xin bản sao Giấy khai sinh")

    result = session.send("Tôi muốn biết đăng ký tạm trú khác gì thủ tục này?")

    assert result.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert "bạn có muốn chuyển" in result.reply.lower()


def test_pending_service_switch_remembers_target_for_short_confirmation(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(procedure_code="2.000635"),
            outcome(procedure_code="1.004194"),
        ),
        repository,
    )
    session.send("Tôi xin bản sao Giấy khai sinh")
    proposed = session.send("Đăng ký tạm trú khác gì thủ tục này?")

    switched = session.send("ok, hãy chuyển cho tôi")

    assert "bạn có muốn chuyển" in proposed.reply.lower()
    assert switched.state.draft.procedure_code is ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION
    assert "đã chuyển sang yêu cầu mới" in switched.reply
    assert len(session.state.messages) == 6
    assert len(session.state.suggestions) == 0


def test_pending_service_switch_can_be_rejected_with_plain_language(
    repository: ProcedureRepository,
) -> None:
    session = ConversationSession(
        StubExtractor(
            outcome(procedure_code="2.000635"),
            outcome(procedure_code="1.004194"),
        ),
        repository,
    )
    session.send("Tôi xin bản sao Giấy khai sinh")
    session.send("Đăng ký tạm trú khác gì thủ tục này?")

    kept = session.send("Không, giữ dịch vụ hiện tại")

    assert kept.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert "giữ nguyên dịch vụ" in kept.reply.lower()


def test_close_clears_state_and_prevents_reuse(repository: ProcedureRepository) -> None:
    session = ConversationSession(StubExtractor(), repository)
    session.close()
    assert session.state.turn_number == 0
    with pytest.raises(RuntimeError, match="closed"):
        session.send("không được xử lý")
