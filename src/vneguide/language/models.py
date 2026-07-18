"""Immutable contracts for Vietnamese text normalization and evidence mapping."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class InputSource(StrEnum):
    """Origin of a user turn; both paths share the same safety contract."""

    TEXT = "text"
    SPEECH = "speech"


class ProtectedKind(StrEnum):
    FULL_NAME = "full_name"
    CCCD = "cccd"
    DATE_OF_BIRTH = "date_of_birth"
    ADDRESS = "address"
    PROCEDURE_CODE = "procedure_code"
    PHONE_NUMBER = "phone_number"
    CASE_CODE = "case_code"


@dataclass(frozen=True, slots=True)
class ProtectedSpan:
    kind: ProtectedKind
    start: int
    end: int
    value: str

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError("protected span offsets are invalid")
        if not self.value:
            raise ValueError("protected span value must not be empty")


@dataclass(frozen=True, slots=True)
class SpanMapping:
    """Map one normalized segment back to the raw user-authored segment."""

    raw_start: int
    raw_end: int
    normalized_start: int
    normalized_end: int
    raw_text: str
    normalized_text: str
    rule_id: str | None = None
    protected_kind: ProtectedKind | None = None

    def __post_init__(self) -> None:
        if self.raw_start < 0 or self.raw_end < self.raw_start:
            raise ValueError("raw mapping offsets are invalid")
        if self.normalized_start < 0 or self.normalized_end < self.normalized_start:
            raise ValueError("normalized mapping offsets are invalid")

    @property
    def changed(self) -> bool:
        return self.raw_text != self.normalized_text


@dataclass(frozen=True, slots=True)
class Ambiguity:
    phrase: str
    options: tuple[str, ...]
    raw_start: int
    raw_end: int

    def __post_init__(self) -> None:
        if not self.phrase or self.raw_start < 0 or self.raw_end <= self.raw_start:
            raise ValueError("ambiguity span is invalid")
        if len(self.options) < 2 or any(not option.strip() for option in self.options):
            raise ValueError("ambiguity must provide at least two non-empty options")


@dataclass(frozen=True, slots=True)
class ModelNormalizationCandidate:
    normalized_text: str
    confidence: float
    ambiguities: tuple[Ambiguity, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.normalized_text, str) or not self.normalized_text.strip():
            raise ValueError("model normalized_text must be non-empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("model confidence must be between zero and one")


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """A normalized turn retained in memory only; callers must not log raw text."""

    raw_text: str
    normalized_text: str
    mappings: tuple[SpanMapping, ...]
    protected_spans: tuple[ProtectedSpan, ...]
    confidence: float
    ambiguities: tuple[Ambiguity, ...]
    input_source: InputSource
    model_assisted: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("normalization confidence must be between zero and one")
        if "".join(mapping.raw_text for mapping in self.mappings) != self.raw_text:
            raise ValueError("mappings must cover raw text without gaps")
        if "".join(mapping.normalized_text for mapping in self.mappings) != self.normalized_text:
            raise ValueError("mappings must cover normalized text without gaps")

    @property
    def changed_spans(self) -> tuple[SpanMapping, ...]:
        return tuple(mapping for mapping in self.mappings if mapping.changed)

    def raw_text_for(self, normalized_evidence: str) -> str | None:
        """Return the smallest raw slice supporting normalized model evidence."""

        if not normalized_evidence:
            return None
        normalized_start = self.normalized_text.casefold().find(normalized_evidence.casefold())
        if normalized_start < 0:
            return None
        normalized_end = normalized_start + len(normalized_evidence)
        raw_ranges: list[tuple[int, int]] = []
        for mapping in self.mappings:
            overlap_start = max(normalized_start, mapping.normalized_start)
            overlap_end = min(normalized_end, mapping.normalized_end)
            if overlap_start >= overlap_end:
                continue
            if len(mapping.raw_text) == len(mapping.normalized_text):
                raw_start = mapping.raw_start + overlap_start - mapping.normalized_start
                raw_end = mapping.raw_start + overlap_end - mapping.normalized_start
            else:
                raw_start, raw_end = mapping.raw_start, mapping.raw_end
            if raw_start < raw_end:
                raw_ranges.append((raw_start, raw_end))
        if not raw_ranges:
            return None
        raw_start = min(item[0] for item in raw_ranges)
        raw_end = max(item[1] for item in raw_ranges)
        return self.raw_text[raw_start:raw_end]

    def clarification_prompt(self) -> str | None:
        if not self.ambiguities:
            return None
        ambiguity = self.ambiguities[0]
        options = "; ".join(f"[{option}]" for option in ambiguity.options)
        return f"Bạn nói “{ambiguity.phrase}”. Bạn đang muốn hỏi: {options}"


__all__ = [
    "Ambiguity",
    "InputSource",
    "ModelNormalizationCandidate",
    "NormalizationResult",
    "ProtectedKind",
    "ProtectedSpan",
    "SpanMapping",
]
