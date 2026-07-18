from __future__ import annotations

from pathlib import Path

from vneguide.core import CatalogReplyComposer
from vneguide.data import ProcedureRepository

from .chat_core_evaluator import evaluate_chat_core, load_cases

ROOT = Path(__file__).resolve().parents[2]


def test_guided_core_improves_fact_coverage_without_extra_model_calls() -> None:
    repository = ProcedureRepository.discover(ROOT)
    cases = load_cases()

    baseline = evaluate_chat_core(
        variant="baseline",
        composer=None,
        repository=repository,
        cases=cases,
    )
    guided = evaluate_chat_core(
        variant="guided",
        composer=CatalogReplyComposer(repository),
        repository=repository,
        cases=cases,
    )

    assert len(cases) == 12
    assert {case.procedure_code.value for case in cases} == {
        "2.000635",
        "1.013314",
        "1.004194",
    }
    assert baseline.expected_fact_coverage == 0
    assert guided.expected_fact_coverage >= 0.85
    assert guided.expected_fact_coverage - baseline.expected_fact_coverage >= 0.25
    assert guided.topic_accuracy == 1
    assert guided.source_grounding_rate == 1
    assert guided.additional_model_calls == 0


def test_ab_report_contains_aggregate_metrics_only() -> None:
    repository = ProcedureRepository.discover(ROOT)
    metrics = evaluate_chat_core(
        variant="guided",
        composer=CatalogReplyComposer(repository),
        repository=repository,
        cases=load_cases(),
    )

    report = metrics.as_report()

    assert report["variant"] == "guided"
    assert report["total_cases"] == 12
    assert "message" not in report
    assert "reply" not in report
    assert "expected_terms" not in report
