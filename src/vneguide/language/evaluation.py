"""Offline evaluation helpers for synthetic dialect-normalization fixtures."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import InputSource, NormalizationResult
from .normalizer import LanguageNormalizer


@dataclass(frozen=True, slots=True)
class DialectEvaluationSample:
    raw_text: str
    expected_intent: str
    expected_normalized_text: str
    protected_values: tuple[str, ...]
    must_not_infer: tuple[str, ...]
    input_source: InputSource = InputSource.TEXT

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> DialectEvaluationSample:
        required = (
            "raw_text",
            "expected_intent",
            "expected_normalized_text",
            "protected_values",
            "must_not_infer",
        )
        if any(key not in payload for key in required):
            raise ValueError("dialect evaluation sample is missing a required property")
        raw_text = payload["raw_text"]
        expected_intent = payload["expected_intent"]
        expected_normalized_text = payload["expected_normalized_text"]
        protected_values = payload["protected_values"]
        must_not_infer = payload["must_not_infer"]
        if not all(
            isinstance(item, str) for item in (raw_text, expected_intent, expected_normalized_text)
        ):
            raise ValueError("dialect evaluation text properties must be strings")
        if not _is_string_list(protected_values) or not _is_string_list(must_not_infer):
            raise ValueError("protected_values and must_not_infer must be string arrays")
        try:
            input_source = InputSource(payload.get("input_source", InputSource.TEXT))
        except ValueError as exc:
            raise ValueError("input_source must be text or speech") from exc
        return cls(
            raw_text=raw_text,
            expected_intent=expected_intent,
            expected_normalized_text=expected_normalized_text,
            protected_values=tuple(protected_values),
            must_not_infer=tuple(must_not_infer),
            input_source=input_source,
        )


@dataclass(frozen=True, slots=True)
class NormalizationEvaluationMetrics:
    sample_count: int
    exact_normalization_rate: float
    raw_intent_accuracy: float
    normalized_intent_accuracy: float
    protected_span_preservation_rate: float
    unsafe_inference_count: int

    @property
    def intent_accuracy_non_decreasing(self) -> bool:
        return self.normalized_intent_accuracy >= self.raw_intent_accuracy

    @property
    def protected_spans_all_preserved(self) -> bool:
        return self.protected_span_preservation_rate == 1.0


IntentClassifier = Callable[[str], str]


def load_dialect_samples(directory: Path) -> tuple[DialectEvaluationSample, ...]:
    """Load every JSONL fixture in a stable order without logging its contents."""

    samples: list[DialectEvaluationSample] = []
    for path in sorted(directory.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSON at {path.name}:{line_number}") from exc
                if not isinstance(payload, Mapping):
                    raise ValueError(f"expected object at {path.name}:{line_number}")
                samples.append(DialectEvaluationSample.from_mapping(payload))
    if not samples:
        raise ValueError(f"no dialect evaluation samples found under {directory}")
    return tuple(samples)


def evaluate_normalizer(
    normalizer: LanguageNormalizer,
    samples: Sequence[DialectEvaluationSample],
    classify_intent: IntentClassifier,
) -> NormalizationEvaluationMetrics:
    """Evaluate behavior in memory; raw or normalized user text is never logged."""

    if not samples:
        raise ValueError("at least one evaluation sample is required")
    exact = 0
    raw_intent_correct = 0
    normalized_intent_correct = 0
    protected_total = 0
    protected_preserved = 0
    unsafe_inference_count = 0

    for sample in samples:
        result = normalizer.normalize(sample.raw_text, source=sample.input_source)
        exact += result.normalized_text == sample.expected_normalized_text
        raw_intent_correct += classify_intent(sample.raw_text) == sample.expected_intent
        normalized_intent_correct += (
            classify_intent(result.normalized_text) == sample.expected_intent
        )
        protected_total += len(sample.protected_values)
        protected_preserved += sum(
            result.normalized_text.count(value) == sample.raw_text.count(value)
            for value in sample.protected_values
        )
        unsafe_inference_count += _count_unsafe_inferences(sample, result)

    sample_count = len(samples)
    preservation_rate = protected_preserved / protected_total if protected_total else 1.0
    return NormalizationEvaluationMetrics(
        sample_count=sample_count,
        exact_normalization_rate=exact / sample_count,
        raw_intent_accuracy=raw_intent_correct / sample_count,
        normalized_intent_accuracy=normalized_intent_correct / sample_count,
        protected_span_preservation_rate=preservation_rate,
        unsafe_inference_count=unsafe_inference_count,
    )


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _count_unsafe_inferences(
    sample: DialectEvaluationSample,
    result: NormalizationResult,
) -> int:
    raw_folded = sample.raw_text.casefold()
    normalized_folded = result.normalized_text.casefold()
    return sum(
        forbidden.casefold() not in raw_folded and forbidden.casefold() in normalized_folded
        for forbidden in sample.must_not_infer
    )


__all__ = [
    "DialectEvaluationSample",
    "IntentClassifier",
    "NormalizationEvaluationMetrics",
    "evaluate_normalizer",
    "load_dialect_samples",
]
