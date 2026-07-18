"""Contract evaluation for deterministic answers over synthetic Q&A routes."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from vneguide.ai import InformationRequest
from vneguide.data import ProcedureRepository
from vneguide.domain import ProcedureCode, QATopic
from vneguide.rules import ProcedureQAResponder

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data" / "evaluation" / "synthetic_grounded_qa.jsonl"


@dataclass(frozen=True, slots=True)
class GroundedQACase:
    case_id: str
    procedure_code: ProcedureCode
    topics: tuple[QATopic, ...]
    target_field_id: str | None
    reference_fields: Mapping[str, str]
    reference_evidence: Mapping[str, str]
    expected_fragments: tuple[str, ...]
    expected_source_ids: tuple[str, ...]


def _text(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_text(raw: Mapping[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is not None and (not isinstance(value, str) or not value):
        raise ValueError(f"{key} must be a non-empty string or null")
    return value


def _strings(raw: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{key} must be an array of non-empty strings")
    return tuple(value)


def _string_mapping(raw: Mapping[str, object], key: str) -> dict[str, str]:
    value = raw.get(key)
    if not isinstance(value, dict) or any(
        not isinstance(item_key, str) or not isinstance(item_value, str)
        for item_key, item_value in value.items()
    ):
        raise ValueError(f"{key} must be an object of strings")
    return dict(value)


def load_cases(path: Path = DATASET) -> tuple[GroundedQACase, ...]:
    cases: list[GroundedQACase] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        decoded = json.loads(line)
        if not isinstance(decoded, dict):
            raise ValueError(f"Q&A case on line {line_number} must be an object")
        raw: Mapping[str, object] = decoded
        expected_keys = {
            "case_id",
            "message",
            "procedure_code",
            "topics",
            "target_field_id",
            "reference_fields",
            "reference_evidence",
            "expected_fragments",
            "expected_source_ids",
        }
        if set(raw) != expected_keys:
            raise ValueError(f"Q&A case on line {line_number} has unexpected keys")
        case_id = _text(raw, "case_id")
        if case_id in seen_ids:
            raise ValueError(f"duplicate Q&A case ID {case_id}")
        seen_ids.add(case_id)
        _text(raw, "message")
        references = _string_mapping(raw, "reference_fields")
        evidence = _string_mapping(raw, "reference_evidence")
        if set(references) != set(evidence):
            raise ValueError(f"Q&A case {case_id} has mismatched reference evidence")
        cases.append(
            GroundedQACase(
                case_id=case_id,
                procedure_code=ProcedureCode(_text(raw, "procedure_code")),
                topics=tuple(QATopic(topic) for topic in _strings(raw, "topics")),
                target_field_id=_optional_text(raw, "target_field_id"),
                reference_fields=references,
                reference_evidence=evidence,
                expected_fragments=_strings(raw, "expected_fragments"),
                expected_source_ids=_strings(raw, "expected_source_ids"),
            )
        )
    if not cases:
        raise ValueError("Q&A evaluation dataset must not be empty")
    return tuple(cases)


CASES = load_cases()


@pytest.mark.parametrize("case", CASES, ids=[case.case_id for case in CASES])
def test_synthetic_grounded_qa_case(case: GroundedQACase) -> None:
    repository = ProcedureRepository.discover(ROOT)
    responder = ProcedureQAResponder(repository)
    answer = responder.answer(
        case.procedure_code,
        InformationRequest(
            topics=case.topics,
            target_field_id=case.target_field_id,
            reference_fields=case.reference_fields,
            evidence=case.reference_evidence,
        ),
    )

    for fragment in case.expected_fragments:
        assert fragment in answer.text, case.case_id
    assert answer.source_ids == case.expected_source_ids
