"""Deterministic A/B metrics for the catalog-guided reply experiment."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from vneguide.core import GuidanceTopic, ReplyComposer
from vneguide.data import ProcedureRepository
from vneguide.domain import ProcedureCode

DEFAULT_CASES_PATH = Path(__file__).with_name("chat_core_ab_cases.json")


@dataclass(frozen=True, slots=True)
class ChatCoreCase:
    case_id: str
    procedure_code: ProcedureCode
    message: str
    expected_topic: GuidanceTopic
    expected_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChatCoreMetrics:
    variant: str
    total_cases: int
    answered_cases: int
    topic_hits: int
    fact_hits: int
    grounded_source_hits: int
    elapsed_ms: float
    additional_model_calls: int = 0

    @property
    def expected_fact_coverage(self) -> float:
        return self.fact_hits / self.total_cases if self.total_cases else 0.0

    @property
    def topic_accuracy(self) -> float:
        return self.topic_hits / self.total_cases if self.total_cases else 0.0

    @property
    def source_grounding_rate(self) -> float:
        return self.grounded_source_hits / self.answered_cases if self.answered_cases else 0.0

    def as_report(self) -> dict[str, object]:
        report: dict[str, object] = asdict(self)
        report.update(
            expected_fact_coverage=round(self.expected_fact_coverage, 4),
            topic_accuracy=round(self.topic_accuracy, 4),
            source_grounding_rate=round(self.source_grounding_rate, 4),
        )
        return report


def load_cases(path: Path = DEFAULT_CASES_PATH) -> tuple[ChatCoreCase, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("chat core A/B cases must be a non-empty array")
    cases: list[ChatCoreCase] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"case {index} must be an object")
        terms = item.get("expected_terms")
        if (
            not isinstance(terms, list)
            or not terms
            or any(not isinstance(term, str) or not term.strip() for term in terms)
        ):
            raise ValueError(f"case {index} expected_terms must be non-empty strings")
        try:
            case = ChatCoreCase(
                case_id=_required_string(item, "case_id", index),
                procedure_code=ProcedureCode(_required_string(item, "procedure_code", index)),
                message=_required_string(item, "message", index),
                expected_topic=GuidanceTopic(_required_string(item, "expected_topic", index)),
                expected_terms=tuple(terms),
            )
        except ValueError as exc:
            raise ValueError(f"case {index} is invalid: {exc}") from exc
        cases.append(case)
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("chat core A/B case IDs must be unique")
    return tuple(cases)


def evaluate_chat_core(
    *,
    variant: str,
    composer: ReplyComposer | None,
    repository: ProcedureRepository,
    cases: tuple[ChatCoreCase, ...],
) -> ChatCoreMetrics:
    started = time.perf_counter()
    answered = 0
    topic_hits = 0
    fact_hits = 0
    source_hits = 0

    for case in cases:
        reply = (
            None
            if composer is None
            else composer.compose(
                procedure_code=case.procedure_code,
                message=case.message,
            )
        )
        if reply is None:
            continue
        answered += 1
        if reply.topic is case.expected_topic:
            topic_hits += 1
        folded_reply = reply.text.casefold()
        if all(term.casefold() in folded_reply for term in case.expected_terms):
            fact_hits += 1
        approved_sources = set(repository.get_by_code(case.procedure_code).source_ids)
        if reply.source_ids and set(reply.source_ids) <= approved_sources:
            source_hits += 1

    elapsed_ms = (time.perf_counter() - started) * 1000
    return ChatCoreMetrics(
        variant=variant,
        total_cases=len(cases),
        answered_cases=answered,
        topic_hits=topic_hits,
        fact_hits=fact_hits,
        grounded_source_hits=source_hits,
        elapsed_ms=round(elapsed_ms, 3),
    )


def _required_string(item: dict[str, Any], key: str, index: int) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"case {index} {key} must be non-empty text")
    return value


__all__ = [
    "ChatCoreCase",
    "ChatCoreMetrics",
    "DEFAULT_CASES_PATH",
    "evaluate_chat_core",
    "load_cases",
]
