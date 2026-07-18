"""Aggregate, privacy-preserving metrics for structured extraction evaluation."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import subprocess
import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Protocol, TypeVar

JsonScalar = str | int | float | bool | None
ContextT = TypeVar("ContextT", contravariant=True)


class OutcomeLike(Protocol):
    """The extractor result surface consumed by this evaluator."""

    @property
    def succeeded(self) -> bool: ...

    @property
    def classification(self) -> str | None: ...

    @property
    def procedure_code(self) -> str | None: ...

    @property
    def fields(self) -> Mapping[str, JsonScalar]: ...

    @property
    def evidence(self) -> Mapping[str, str]: ...

    @property
    def context_signals(self) -> Mapping[str, JsonScalar]: ...

    @property
    def context_evidence(self) -> Mapping[str, str]: ...

    @property
    def error_code(self) -> str | None: ...


class ExtractorLike(Protocol[ContextT]):
    """A context-aware extractor, real or fake."""

    def extract(self, message: str, *, context: ContextT) -> OutcomeLike: ...


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    active_procedure_code: str | None
    target_field_id: str | None


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    case_id: str
    conversation_id: str
    turn_index: int
    message: str
    context: EvaluationContext
    expected_classification: str
    expected_procedure_code: str | None
    expected_fields: Mapping[str, JsonScalar]
    expected_context_signals: Mapping[str, JsonScalar]


def load_cases(path: Path) -> tuple[EvaluationCase, ...]:
    """Load strict synthetic JSONL cases without accepting unknown keys or PII metadata."""

    expected_keys = {
        "case_id",
        "conversation_id",
        "turn_index",
        "message",
        "context",
        "expected_classification",
        "expected_procedure_code",
        "expected_fields",
        "expected_context_signals",
    }
    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError("Evaluation dataset could not be read as UTF-8.") from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except (json.JSONDecodeError, RecursionError) as exc:
            raise ValueError(f"Invalid evaluation JSON on line {line_number}.") from exc
        if not isinstance(raw, dict) or set(raw) != expected_keys:
            raise ValueError(f"Evaluation case on line {line_number} has unexpected keys.")
        context = raw["context"]
        if not isinstance(context, dict) or set(context) != {
            "active_procedure_code",
            "target_field_id",
        }:
            raise ValueError(f"Evaluation context on line {line_number} is invalid.")

        case_id = _required_string(raw["case_id"], "case_id", line_number)
        if case_id in seen_ids:
            raise ValueError(f"Duplicate evaluation case ID on line {line_number}.")
        seen_ids.add(case_id)
        classification = _required_string(
            raw["expected_classification"], "expected_classification", line_number
        )
        if classification not in {"supported", "unsupported", "ambiguous"}:
            raise ValueError(f"Unknown expected classification on line {line_number}.")
        procedure_code = _optional_string(
            raw["expected_procedure_code"], "expected_procedure_code", line_number
        )
        active_procedure_code = _optional_string(
            context["active_procedure_code"], "active_procedure_code", line_number
        )
        target_field_id = _optional_string(
            context["target_field_id"], "target_field_id", line_number
        )
        turn_index = raw["turn_index"]
        if type(turn_index) is not int or turn_index < 1:
            raise ValueError(f"turn_index on line {line_number} must be a positive integer.")
        expected_fields = _scalar_mapping(raw["expected_fields"], "expected_fields", line_number)
        expected_signals = _scalar_mapping(
            raw["expected_context_signals"], "expected_context_signals", line_number
        )
        if classification != "supported" and (
            procedure_code is not None or expected_fields or expected_signals
        ):
            raise ValueError(
                f"Non-supported evaluation case on line {line_number} contains unsafe slots."
            )
        if classification == "supported" and procedure_code is None:
            raise ValueError(
                f"Supported evaluation case on line {line_number} needs a procedure code."
            )
        cases.append(
            EvaluationCase(
                case_id=case_id,
                conversation_id=_required_string(
                    raw["conversation_id"], "conversation_id", line_number
                ),
                turn_index=turn_index,
                message=_required_string(raw["message"], "message", line_number),
                context=EvaluationContext(active_procedure_code, target_field_id),
                expected_classification=classification,
                expected_procedure_code=procedure_code,
                expected_fields=expected_fields,
                expected_context_signals=expected_signals,
            )
        )
    if not cases:
        raise ValueError("Evaluation dataset must contain at least one case.")
    return tuple(cases)


def dataset_sha256(path: Path) -> str:
    """Hash UTF-8 text with the data-package LF normalization convention."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError("Evaluation dataset could not be hashed.") from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def verify_dataset_sha256(dataset_path: Path, manifest_path: Path) -> str:
    """Fail closed unless the fixed fixture matches its LF-normalized QA manifest."""

    try:
        manifest = manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError("Evaluation dataset integrity check failed.") from exc
    match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)\r?\n?", manifest)
    if match is None or match.group(2) != dataset_path.name:
        raise ValueError("Evaluation dataset integrity check failed.")
    actual_digest = dataset_sha256(dataset_path)
    if not hmac.compare_digest(actual_digest, match.group(1)):
        raise ValueError("Evaluation dataset integrity check failed.")
    return actual_digest


def repository_state(repository_root: Path) -> tuple[str, bool]:
    """Resolve Git revision and dirty state without exposing environment values."""

    try:
        revision_result = subprocess.run(
            ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        status_result = subprocess.run(
            ["git", "-C", str(repository_root), "status", "--porcelain=v1"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("Repository state could not be resolved.") from exc
    revision = revision_result.stdout.strip()
    if (
        revision_result.returncode != 0
        or status_result.returncode != 0
        or re.fullmatch(r"[0-9a-fA-F]{40}", revision) is None
    ):
        raise ValueError("Repository state could not be resolved.")
    return revision.lower(), bool(status_result.stdout.strip())


def evaluate_cases(
    extractor: ExtractorLike[ContextT],
    cases: Sequence[EvaluationCase],
    *,
    context_factory: Callable[[str | None, str | None], ContextT],
    provider: str,
    model: str | None,
    dataset_id: str,
    dataset_digest: str,
    revision: str | None = None,
    working_tree_dirty: bool | None = None,
    generated_at: datetime | None = None,
    timer: Callable[[], float] = perf_counter,
) -> dict[str, object]:
    """Run cases and return aggregate metrics without retaining messages or raw outputs."""

    if not cases:
        raise ValueError("At least one evaluation case is required.")
    if not provider.strip() or not dataset_id.strip() or not dataset_digest.strip():
        raise ValueError("Provider and dataset metadata must be non-empty.")
    if revision is not None and not revision.strip():
        raise ValueError("Revision must be null or a non-empty string.")

    intent_matches = 0
    procedure_matches = 0
    procedure_case_count = 0
    fallback_count = 0
    exception_count = 0
    true_positive = 0
    false_positive = 0
    false_negative = 0
    grounded_slot_count = 0
    predicted_slot_count = 0
    latencies_ms: list[float] = []

    for case in cases:
        context = context_factory(
            case.context.active_procedure_code,
            case.context.target_field_id,
        )
        started = timer()
        outcome: OutcomeLike | None
        try:
            outcome = extractor.extract(case.message, context=context)
        except Exception:  # The aggregate report must survive one provider/adapter failure.
            outcome = None
            exception_count += 1
        elapsed_ms = max(0.0, (timer() - started) * 1_000.0)
        latencies_ms.append(elapsed_ms)

        expected_slots = _namespaced_slots(
            case.expected_fields,
            case.expected_context_signals,
        )
        if outcome is None:
            fallback_count += 1
            false_negative += len(expected_slots)
            if case.expected_procedure_code is not None:
                procedure_case_count += 1
            continue

        if not outcome.succeeded:
            fallback_count += 1
        if outcome.classification == case.expected_classification:
            intent_matches += 1
        if case.expected_procedure_code is not None:
            procedure_case_count += 1
            if outcome.procedure_code == case.expected_procedure_code:
                procedure_matches += 1

        predicted_slots = _namespaced_slots(outcome.fields, outcome.context_signals)
        matches, extra, missing = _slot_counts(expected_slots, predicted_slots)
        true_positive += matches
        false_positive += extra
        false_negative += missing

        evidence = {
            **{f"field:{key}": value for key, value in outcome.evidence.items()},
            **{f"context_signal:{key}": value for key, value in outcome.context_evidence.items()},
        }
        predicted_slot_count += len(predicted_slots)
        grounded_slot_count += sum(
            1
            for slot_id in predicted_slots
            if _contains_evidence(case.message, evidence.get(slot_id))
        )

    slot_precision = _safe_divide(true_positive, true_positive + false_positive)
    slot_recall = _safe_divide(true_positive, true_positive + false_negative)
    slot_f1 = _safe_divide(2.0 * slot_precision * slot_recall, slot_precision + slot_recall)
    timestamp = generated_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware.")

    return {
        "schema_version": "1.0",
        "generated_at": timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "provider": provider,
        "model": model,
        "revision": revision,
        "working_tree_dirty": working_tree_dirty,
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_digest,
        "case_count": len(cases),
        "metrics": {
            "intent_accuracy": _safe_divide(intent_matches, len(cases)),
            "procedure_accuracy": _safe_divide(procedure_matches, procedure_case_count),
            "slot_precision": slot_precision,
            "slot_recall": slot_recall,
            "slot_f1": slot_f1,
            "grounding_success_rate": _safe_divide(grounded_slot_count, predicted_slot_count),
            "fallback_rate": _safe_divide(fallback_count, len(cases)),
        },
        "counts": {
            "procedure_case_count": procedure_case_count,
            "slot_true_positive": true_positive,
            "slot_false_positive": false_positive,
            "slot_false_negative": false_negative,
            "grounded_slot_count": grounded_slot_count,
            "predicted_slot_count": predicted_slot_count,
            "fallback_count": fallback_count,
            "exception_count": exception_count,
        },
        "latency_ms": {
            "mean": _mean(latencies_ms),
            "p50": _nearest_rank_percentile(latencies_ms, 0.50),
            "p95": _nearest_rank_percentile(latencies_ms, 0.95),
            "max": max(latencies_ms),
        },
    }


def _required_string(value: object, name: str, line_number: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} on line {line_number} must be a non-empty string.")
    return value


def _optional_string(value: object, name: str, line_number: int) -> str | None:
    if value is None:
        return None
    return _required_string(value, name, line_number)


def _scalar_mapping(value: object, name: str, line_number: int) -> dict[str, JsonScalar]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} on line {line_number} must be an object.")
    result: dict[str, JsonScalar] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key or not _is_json_scalar(item):
            raise ValueError(f"{name} on line {line_number} has an invalid slot.")
        result[key] = item
    return result


def _is_json_scalar(value: object) -> bool:
    if value is None or isinstance(value, (str, bool)):
        return True
    if type(value) is int:
        return True
    return isinstance(value, float) and math.isfinite(value)


def _namespaced_slots(
    fields: Mapping[str, JsonScalar], signals: Mapping[str, JsonScalar]
) -> dict[str, JsonScalar]:
    return {
        **{f"field:{key}": value for key, value in fields.items()},
        **{f"context_signal:{key}": value for key, value in signals.items()},
    }


def _slot_counts(
    expected: Mapping[str, JsonScalar], predicted: Mapping[str, JsonScalar]
) -> tuple[int, int, int]:
    matches = 0
    false_positive = 0
    false_negative = 0
    for slot_id in expected.keys() | predicted.keys():
        has_expected = slot_id in expected
        has_predicted = slot_id in predicted
        if has_expected and has_predicted and _same_scalar(expected[slot_id], predicted[slot_id]):
            matches += 1
        else:
            false_positive += int(has_predicted)
            false_negative += int(has_expected)
    return matches, false_positive, false_negative


def _same_scalar(expected: JsonScalar, predicted: JsonScalar) -> bool:
    if type(expected) in (int, float) and type(predicted) in (int, float):
        return expected == predicted
    return type(expected) is type(predicted) and expected == predicted


def _contains_evidence(message: str, evidence: str | None) -> bool:
    if evidence is None or not evidence.strip():
        return False
    return _normalise(evidence) in _normalise(message)


def _normalise(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _mean(values: Iterable[float]) -> float:
    materialized = tuple(values)
    return sum(materialized) / len(materialized) if materialized else 0.0


def _nearest_rank_percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


__all__ = [
    "EvaluationCase",
    "EvaluationContext",
    "ExtractorLike",
    "OutcomeLike",
    "dataset_sha256",
    "evaluate_cases",
    "load_cases",
    "repository_state",
    "verify_dataset_sha256",
]
