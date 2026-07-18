from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from vneguide.data import ProcedureRepository
from vneguide.domain import FieldType, ProcedureCode, RuleInputOrigin, SourceStatus
from vneguide.rules import RULE_HANDLERS, QuestionSelector, RuleEngine

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def repository() -> ProcedureRepository:
    return ProcedureRepository.discover(ROOT)


@pytest.fixture(scope="module")
def engine(repository: ProcedureRepository) -> RuleEngine:
    return RuleEngine(repository, today=date(2026, 7, 17))


def test_every_reviewed_rule_has_exactly_one_handler(repository: ProcedureRepository) -> None:
    reviewed = {
        rule.rule_id
        for procedure in repository.list_procedures()
        for rule in repository.rules_for(procedure.procedure_code)
    }
    assert set(RULE_HANDLERS) == reviewed


def test_every_business_rule_traces_to_an_approved_source(
    repository: ProcedureRepository,
) -> None:
    for procedure in repository.list_procedures():
        for rule in repository.rules_for(procedure.procedure_code):
            assert rule.source_ids, rule.rule_id
            for source_id in rule.source_ids:
                source = repository.get_source(source_id)
                assert source.status is SourceStatus.APPROVED, rule.rule_id
                assert source.procedure_code in (None, procedure.procedure_code.value), rule.rule_id


def test_gold_validation_cases(engine: RuleEngine) -> None:
    path = ROOT / "data" / "evaluation" / "gold_validation.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        result = engine.validate(
            case["procedure_code"],
            case["input"],
            context_signals=case.get("context_signals"),
            context_origins=case.get("context_origins"),
            confirmed_context_signal_ids={
                input_id
                for input_id, origin in case.get("context_origins", {}).items()
                if origin in {"intent_extraction", "user_declaration"}
            },
            trusted_adapter_signal_ids={
                input_id
                for input_id, origin in case.get("context_origins", {}).items()
                if origin in {"document_check", "derived"}
            },
        )
        assert result.status.value == case["expected_status"], case["case_id"]
        assert {issue.rule_id for issue in result.issues} == set(case["expected_rule_ids"]), case[
            "case_id"
        ]


def test_missing_fields_follow_reviewed_order_and_conditions(
    engine: RuleEngine,
) -> None:
    missing = engine.missing_fields(ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION, {})
    assert missing[:4] == (
        "registration_mode",
        "applicant_full_name",
        "applicant_date_of_birth",
        "applicant_personal_id",
    )
    conditional = engine.missing_fields(
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        {"applicant_is_minor": True, "legal_dwelling_data_retrievable": False},
    )
    assert "minor_consent_present" in conditional
    assert "legal_dwelling_document_present" in conditional


def test_question_selector_explains_catalog_choices_in_plain_vietnamese(
    repository: ProcedureRepository,
) -> None:
    selector = QuestionSelector(repository)
    expected_enum_labels = {
        ("2.000635", "requester_type"): (
            "cá nhân tự yêu cầu",
            "người được ủy quyền",
            "đại diện tổ chức",
        ),
        ("2.000635", "requester_id_document_type"): (
            "căn cước công dân",
            "chứng minh nhân dân",
            "hộ chiếu",
            "giấy chứng nhận căn cước",
            "căn cước điện tử",
        ),
        ("2.000635", "submission_channel"): (
            "trực tuyến",
            "trực tiếp",
            "qua bưu chính",
        ),
        ("2.000635", "authorization_relationship"): (
            "ông hoặc bà",
            "cha hoặc mẹ",
            "con",
            "vợ hoặc chồng",
            "anh, chị hoặc em ruột",
            "khác",
        ),
        ("1.013314", "hanoi_zone"): (
            "nội thành Hà Nội",
            "ngoại thành Hà Nội",
        ),
        ("1.004194", "registration_mode"): (
            "cá nhân hoặc hộ gia đình",
            "theo danh sách",
            "đơn vị lực lượng vũ trang",
        ),
        ("1.004194", "dwelling_basis"): (
            "sở hữu",
            "thuê",
            "mượn",
            "ở nhờ",
            "về ở cùng hộ gia đình",
            "khác",
        ),
        ("1.004194", "submission_channel"): ("trực tuyến", "trực tiếp"),
    }

    registration = selector.question_for("1.004194", "registration_mode")
    requester = selector.question_for("2.000635", "requester_type")
    boolean = selector.question_for("1.004194", "applicant_is_minor")

    assert "cá nhân hoặc hộ gia đình" in registration
    assert "theo danh sách" in registration
    assert "đơn vị lực lượng vũ trang" in registration
    assert "cá nhân tự yêu cầu" in requester
    assert "người được ủy quyền" in requester
    assert "đại diện tổ chức" in requester
    assert "Có hoặc Không" in boolean

    seen_enum_fields: set[tuple[str, str]] = set()
    for procedure in repository.list_procedures():
        for field in repository.fields_for(procedure.procedure_code):
            if field.field_type is not FieldType.ENUM:
                continue
            question = selector.question_for(procedure.procedure_code, field.field_id)
            key = (procedure.procedure_code.value, field.field_id)
            seen_enum_fields.add(key)
            assert question.startswith("Anh/chị chọn ")
            assert all(label in question for label in expected_enum_labels[key])
            assert all(str(value) not in question for value in field.values)
    assert seen_enum_fields == set(expected_enum_labels)

    boolean_fields = {
        (procedure.procedure_code, field.field_id)
        for procedure in repository.list_procedures()
        for field in repository.fields_for(procedure.procedure_code)
        if field.field_type is FieldType.BOOLEAN
    }
    assert len(boolean_fields) == 9
    for code, field_id in boolean_fields:
        question = selector.question_for(code, field_id)
        assert "Có" in question
        assert "Không" in question
        assert field_id not in question
        assert "xác nhận mục" not in question


def test_conversation_procedure_labels_are_short_and_centralized(
    repository: ProcedureRepository,
) -> None:
    selector = QuestionSelector(repository)

    labels = {code: selector.procedure_label(code) for code in ProcedureCode}

    assert labels[ProcedureCode.BIRTH_CERTIFICATE_COPY] == "cấp bản sao Giấy khai sinh"
    assert labels[ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION] == "đăng ký tạm trú"
    assert labels[ProcedureCode.HOUSING_CONDITION_CONFIRMATION] == (
        "xác nhận điều kiện nhà ở để đăng ký thường trú"
    )
    assert all(len(label) < 60 for label in labels.values())


def test_field_validation_rejects_bad_identity_and_future_birth_date(
    engine: RuleEngine,
) -> None:
    with pytest.raises(ValueError, match="required format"):
        engine.validate_field_value(
            ProcedureCode.BIRTH_CERTIFICATE_COPY, "requester_personal_id", "123"
        )
    with pytest.raises(ValueError, match="future"):
        engine.validate_field_value(
            ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
            "applicant_date_of_birth",
            "2027-01-01",
        )


def test_temporary_residence_dates_may_start_in_future(engine: RuleEngine) -> None:
    result = engine.validate(
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        {"temporary_start_date": "2027-01-01", "temporary_end_date": "2027-12-31"},
    )
    assert "TEMP-DATE-001" not in {issue.rule_id for issue in result.issues}


def test_rule_context_signals_are_separate_typed_and_origin_checked(
    engine: RuleEngine,
) -> None:
    with pytest.raises(ValueError, match="requires confirmation"):
        engine.validate(
            ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
            {},
            context_signals={"newly_naturalized_or_restored_citizenship": True},
            context_origins={
                "newly_naturalized_or_restored_citizenship": RuleInputOrigin.USER_DECLARATION
            },
        )

    result = engine.validate(
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        {},
        context_signals={"newly_naturalized_or_restored_citizenship": True},
        context_origins={
            "newly_naturalized_or_restored_citizenship": RuleInputOrigin.USER_DECLARATION
        },
        confirmed_context_signal_ids={"newly_naturalized_or_restored_citizenship"},
    )
    assert "TEMP-CITIZENSHIP-001" in {issue.rule_id for issue in result.issues}

    document_result = engine.validate(
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        {},
        context_signals={"ct01_missing": True},
        context_origins={"ct01_missing": RuleInputOrigin.DOCUMENT_CHECK},
        trusted_adapter_signal_ids={"ct01_missing"},
    )
    assert "TEMP-FORM-001" in {issue.rule_id for issue in document_result.issues}

    with pytest.raises(ValueError, match="requires origin"):
        engine.validate(
            ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
            {},
            context_signals={"ct01_missing": True},
            context_origins={"ct01_missing": RuleInputOrigin.USER_DECLARATION},
            confirmed_context_signal_ids={"ct01_missing"},
        )
    with pytest.raises(ValueError, match="must be a boolean"):
        engine.validate_context_signal(
            ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
            "ct01_missing",
            "yes",
            origin=RuleInputOrigin.DOCUMENT_CHECK,
        )
    with pytest.raises(ValueError, match="requires one declared origin"):
        engine.validate(
            ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
            {},
            context_signals={"ct01_missing": True},
            trusted_adapter_signal_ids={"ct01_missing"},
        )
    with pytest.raises(ValueError, match="passed separately with provenance"):
        engine.validate(
            ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
            {"ct01_missing": True},
        )

    with pytest.raises(ValueError, match="trusted provenance"):
        engine.validate(
            ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
            {},
            context_signals={"ct01_missing": True},
            context_origins={"ct01_missing": RuleInputOrigin.DOCUMENT_CHECK},
        )
    with pytest.raises(ValueError, match="was not supplied"):
        engine.validate(
            ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
            {},
            confirmed_context_signal_ids={"not_present"},
        )
    with pytest.raises(ValueError, match="two promotion paths"):
        engine.validate(
            ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
            {},
            context_signals={"ct01_missing": True},
            context_origins={"ct01_missing": RuleInputOrigin.DOCUMENT_CHECK},
            confirmed_context_signal_ids={"ct01_missing"},
            trusted_adapter_signal_ids={"ct01_missing"},
        )
