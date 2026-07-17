from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from vneguide.data import ProcedureRepository
from vneguide.domain import ProcedureCode
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


def test_gold_validation_cases(engine: RuleEngine) -> None:
    path = ROOT / "data" / "evaluation" / "gold_validation.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        result = engine.validate(case["procedure_code"], case["input"])
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
