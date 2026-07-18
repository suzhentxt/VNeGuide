"""Run the deterministic baseline-versus-guided reply evaluation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from vneguide.core import CatalogReplyComposer
from vneguide.data import ProcedureRepository

from .chat_core_evaluator import evaluate_chat_core, load_cases

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
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
    delta = guided.expected_fact_coverage - baseline.expected_fact_coverage
    report = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "engine": "catalog-deterministic",
        "model": None,
        "baseline": baseline.as_report(),
        "guided": guided.as_report(),
        "expected_fact_coverage_delta": round(delta, 4),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    passed = (
        guided.expected_fact_coverage >= 0.85
        and delta >= 0.25
        and guided.source_grounding_rate == 1.0
        and guided.additional_model_calls == 0
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
