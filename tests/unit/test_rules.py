from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from vneguide.data import ProcedureRepository
from vneguide.domain import ProcedureCode, RuleInputOrigin, SourceStatus
from vneguide.rules import RULE_HANDLERS, RuleEngine

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
