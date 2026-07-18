from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from . import run_live_extraction_eval as live_runner
from .extraction_evaluator import (
    EvaluationCase,
    EvaluationContext,
    JsonScalar,
    dataset_sha256,
    evaluate_cases,
    load_cases,
    repository_state,
    verify_dataset_sha256,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPOSITORY_ROOT / "data" / "evaluation" / ("synthetic_multiturn_extraction.jsonl")


@dataclass(frozen=True)
class FakeContext:
    active_procedure_code: str | None
    target_field_id: str | None


@dataclass(frozen=True)
class FakeOutcome:
    succeeded: bool
    classification: str | None
    procedure_code: str | None
    fields: Mapping[str, JsonScalar]
    evidence: Mapping[str, str]
    context_signals: Mapping[str, JsonScalar]
    context_evidence: Mapping[str, str]
    error_code: str | None = None


class FakeExtractor:
    def __init__(self, responses: list[FakeOutcome | Exception]) -> None:
        self._responses = iter(responses)
        self.calls: list[tuple[str, FakeContext]] = []

    def extract(self, message: str, *, context: FakeContext) -> FakeOutcome:
        self.calls.append((message, context))
        response = next(self._responses)
        if isinstance(response, Exception):
            raise response
        return response


def _case(
    case_id: str,
    *,
    message: str,
    classification: str,
    procedure_code: str | None,
    fields: Mapping[str, JsonScalar] | None = None,
    signals: Mapping[str, JsonScalar] | None = None,
    context: EvaluationContext | None = None,
) -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        conversation_id="synthetic",
        turn_index=1,
        message=message,
        context=context or EvaluationContext(None, None),
        expected_classification=classification,
        expected_procedure_code=procedure_code,
        expected_fields=fields or {},
        expected_context_signals=signals or {},
    )


def test_checked_in_dataset_is_synthetic_contextual_and_covers_scope() -> None:
    cases = load_cases(DATASET_PATH)

    assert len(cases) == 21
    assert len({case.case_id for case in cases}) == len(cases)
    assert {case.expected_procedure_code for case in cases if case.expected_procedure_code} == {
        "2.000635",
        "1.013314",
        "1.004194",
    }
    assert {case.expected_classification for case in cases} == {
        "supported",
        "unsupported",
        "ambiguous",
    }
    assert any(case.context.target_field_id is not None for case in cases)
    assert any(case.expected_context_signals for case in cases)
    assert {case.case_id for case in cases if case.case_id.startswith("REG-")} == {
        "REG-NORTH-01",
        "REG-CENTRAL-01",
        "REG-SOUTH-01",
    }
    expected_digest = (
        (REPOSITORY_ROOT / "data" / "qa" / "synthetic_multiturn_extraction.jsonl.sha256")
        .read_text(encoding="utf-8")
        .split()[0]
    )
    assert dataset_sha256(DATASET_PATH) == expected_digest
    assert (
        verify_dataset_sha256(
            DATASET_PATH,
            REPOSITORY_ROOT / "data" / "qa" / "synthetic_multiturn_extraction.jsonl.sha256",
        )
        == expected_digest
    )
    revision, dirty = repository_state(REPOSITORY_ROOT)
    assert len(revision) == 40
    assert isinstance(dirty, bool)


def test_checked_in_slots_match_catalog_and_text_signals_have_safe_origins() -> None:
    cases = load_cases(DATASET_PATH)
    field_records = json.loads(
        (REPOSITORY_ROOT / "data" / "catalog" / "field_catalog.json").read_text(encoding="utf-8")
    )
    signal_records = json.loads(
        (REPOSITORY_ROOT / "data" / "catalog" / "rule_context_catalog.json").read_text(
            encoding="utf-8"
        )
    )
    reviewed_fields = {(record["procedure_code"], record["field_id"]) for record in field_records}
    reviewed_signals = {
        (record["procedure_code"], record["input_id"]): record["origin"]
        for record in signal_records
    }

    for case in cases:
        procedure_code = case.expected_procedure_code
        for field_id in case.expected_fields:
            assert (procedure_code, field_id) in reviewed_fields
        if case.context.target_field_id is not None:
            assert (
                case.context.active_procedure_code,
                case.context.target_field_id,
            ) in reviewed_fields
        for input_id in case.expected_context_signals:
            assert reviewed_signals[(procedure_code, input_id)] in {
                "intent_extraction",
                "user_declaration",
            }


def test_evaluator_computes_exact_slot_grounding_fallback_and_latency_metrics() -> None:
    cases = (
        _case(
            "A",
            message="alpha 1 beta signal",
            classification="supported",
            procedure_code="p1",
            fields={"a": 1, "b": "expected"},
            signals={"s": True},
            context=EvaluationContext("p1", "a"),
        ),
        _case(
            "B",
            message="unsupported request",
            classification="unsupported",
            procedure_code=None,
        ),
        _case(
            "C",
            message="delta 4",
            classification="supported",
            procedure_code="p2",
            fields={"d": 4},
        ),
    )
    extractor = FakeExtractor(
        [
            FakeOutcome(
                succeeded=True,
                classification="supported",
                procedure_code="p1",
                fields={"a": 1, "b": "wrong", "c": "extra"},
                evidence={"a": "1", "b": "beta", "c": "not in message"},
                context_signals={"s": True},
                context_evidence={"s": "signal"},
            ),
            RuntimeError("synthetic provider failure"),
            FakeOutcome(
                succeeded=True,
                classification="unsupported",
                procedure_code=None,
                fields={},
                evidence={},
                context_signals={},
                context_evidence={},
            ),
        ]
    )
    times = iter((0.00, 0.01, 0.01, 0.04, 0.04, 0.06))

    report = evaluate_cases(
        extractor,
        cases,
        context_factory=FakeContext,
        provider="fake-provider",
        model="fake-model-v1",
        dataset_id="in-memory",
        dataset_digest="a" * 64,
        revision="c" * 40,
        working_tree_dirty=False,
        generated_at=datetime(2026, 7, 18, 12, 0, tzinfo=UTC),
        timer=lambda: next(times),
    )

    assert report["generated_at"] == "2026-07-18T12:00:00Z"
    assert report["provider"] == "fake-provider"
    assert report["model"] == "fake-model-v1"
    assert report["revision"] == "c" * 40
    assert report["working_tree_dirty"] is False
    assert report["case_count"] == 3
    metrics = cast(dict[str, float], report["metrics"])
    assert metrics["intent_accuracy"] == pytest.approx(1 / 3)
    assert metrics["procedure_accuracy"] == pytest.approx(1 / 2)
    assert metrics["slot_precision"] == pytest.approx(1 / 2)
    assert metrics["slot_recall"] == pytest.approx(1 / 2)
    assert metrics["slot_f1"] == pytest.approx(1 / 2)
    assert metrics["grounding_success_rate"] == pytest.approx(3 / 4)
    assert metrics["fallback_rate"] == pytest.approx(1 / 3)
    counts = cast(dict[str, int], report["counts"])
    assert counts == {
        "procedure_case_count": 2,
        "slot_true_positive": 2,
        "slot_false_positive": 2,
        "slot_false_negative": 2,
        "grounded_slot_count": 3,
        "predicted_slot_count": 4,
        "fallback_count": 1,
        "exception_count": 1,
    }
    latency = cast(dict[str, float], report["latency_ms"])
    assert latency["mean"] == pytest.approx(20.0)
    assert latency["p50"] == pytest.approx(20.0)
    assert latency["p95"] == pytest.approx(30.0)
    assert latency["max"] == pytest.approx(30.0)
    assert extractor.calls[0][1] == FakeContext("p1", "a")


def test_evaluator_uses_zero_for_metrics_without_slot_or_procedure_denominators() -> None:
    case = _case(
        "empty",
        message="unknown request",
        classification="unsupported",
        procedure_code=None,
    )
    extractor = FakeExtractor(
        [
            FakeOutcome(
                succeeded=True,
                classification="unsupported",
                procedure_code=None,
                fields={},
                evidence={},
                context_signals={},
                context_evidence={},
            )
        ]
    )
    times = iter((1.0, 1.0))

    report = evaluate_cases(
        extractor,
        (case,),
        context_factory=FakeContext,
        provider="fake",
        model=None,
        dataset_id="empty",
        dataset_digest="b" * 64,
        timer=lambda: next(times),
    )

    metrics = cast(dict[str, float], report["metrics"])
    assert metrics == {
        "intent_accuracy": 1.0,
        "procedure_accuracy": 0.0,
        "slot_precision": 0.0,
        "slot_recall": 0.0,
        "slot_f1": 0.0,
        "grounding_success_rate": 0.0,
        "fallback_rate": 0.0,
    }


def test_numeric_int_and_float_slots_match_while_boolean_remains_strict() -> None:
    case = _case(
        "numeric",
        message="20 và 1",
        classification="supported",
        procedure_code="p1",
        fields={"area": 20, "declared": True},
    )
    extractor = FakeExtractor(
        [
            FakeOutcome(
                succeeded=True,
                classification="supported",
                procedure_code="p1",
                fields={"area": 20.0, "declared": 1},
                evidence={"area": "20", "declared": "1"},
                context_signals={},
                context_evidence={},
            )
        ]
    )
    times = iter((1.0, 1.0))

    report = evaluate_cases(
        extractor,
        (case,),
        context_factory=FakeContext,
        provider="fake",
        model=None,
        dataset_id="numeric",
        dataset_digest="d" * 64,
        timer=lambda: next(times),
    )

    metrics = cast(dict[str, float], report["metrics"])
    assert metrics["slot_precision"] == pytest.approx(0.5)
    assert metrics["slot_recall"] == pytest.approx(0.5)
    assert metrics["slot_f1"] == pytest.approx(0.5)


def test_live_runner_rejects_checksum_mismatch_before_provider_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture = tmp_path / "synthetic_multiturn_extraction.jsonl"
    fixture.write_text("RAW-SYNTHETIC-SENTINEL\n", encoding="utf-8")
    manifest = tmp_path / "synthetic_multiturn_extraction.jsonl.sha256"
    manifest.write_text(f"{'0' * 64}  {fixture.name}\n", encoding="utf-8")
    forbidden_calls: list[str] = []

    def forbidden(name: str) -> object:
        forbidden_calls.append(name)
        raise AssertionError(f"{name} must not run before fixture verification")

    monkeypatch.setattr(live_runner, "DEFAULT_CASES_PATH", fixture)
    monkeypatch.setattr(live_runner, "DATASET_CHECKSUM_PATH", manifest)
    monkeypatch.setattr(
        live_runner,
        "load_llm_config",
        lambda **kwargs: forbidden("config"),
    )
    monkeypatch.setattr(
        live_runner,
        "build_llm_provider",
        lambda *args, **kwargs: forbidden("provider"),
    )
    monkeypatch.setattr(
        live_runner,
        "evaluate_cases",
        lambda *args, **kwargs: forbidden("evaluate"),
    )

    with pytest.raises(SystemExit) as caught:
        live_runner.main(["--confirm-live"])

    assert caught.value.code == 2
    assert forbidden_calls == []
    stderr = capsys.readouterr().err
    assert "fixture integrity check failed" in stderr
    assert "RAW-SYNTHETIC-SENTINEL" not in stderr


def test_loader_rejects_non_supported_cases_that_smuggle_slots(tmp_path: Path) -> None:
    path = tmp_path / "unsafe.jsonl"
    path.write_text(
        '{"case_id":"unsafe","conversation_id":"x","turn_index":1,'
        '"message":"x","context":{"active_procedure_code":null,'
        '"target_field_id":null},"expected_classification":"unsupported",'
        '"expected_procedure_code":null,"expected_fields":{"invented":true},'
        '"expected_context_signals":{}}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsafe slots"):
        load_cases(path)
