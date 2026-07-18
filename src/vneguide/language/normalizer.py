"""Two-tier normalization with protected spans and raw evidence traceability."""

from __future__ import annotations

import difflib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vneguide.ai.providers.base import LLMProvider

from .glossary import Glossary, GlossaryEntry, default_glossary
from .models import (
    Ambiguity,
    InputSource,
    ModelNormalizationCandidate,
    NormalizationResult,
    ProtectedSpan,
    SpanMapping,
)
from .protected_spans import detect_protected_spans


@runtime_checkable
class ModelNormalizer(Protocol):
    def normalize(self, protected_text: str) -> ModelNormalizationCandidate:
        """Normalize placeholder-protected text or raise a typed provider error."""


class ModelNormalizationUnavailable(RuntimeError):
    """The optional second tier could not return a safe normalization."""


_MODEL_SCHEMA: Mapping[str, Any] = MappingProxyType(
    {
        "type": "object",
        "additionalProperties": False,
        "required": ["normalized_text", "changed_spans", "confidence", "ambiguities"],
        "properties": {
            "normalized_text": {"type": "string", "minLength": 1, "maxLength": 8_000},
            "changed_spans": {
                "type": "array",
                "maxItems": 64,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["start", "end", "original", "normalized"],
                    "properties": {
                        "start": {"type": "integer", "minimum": 0},
                        "end": {"type": "integer", "minimum": 0},
                        "original": {"type": "string"},
                        "normalized": {"type": "string"},
                    },
                },
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "ambiguities": {
                "type": "array",
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["phrase", "options"],
                    "properties": {
                        "phrase": {"type": "string", "minLength": 1},
                        "options": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 5,
                            "items": {"type": "string", "minLength": 1},
                        },
                    },
                },
            },
        },
    }
)

_MODEL_PROMPT = """Bạn chỉ chuẩn hóa tiếng Việt phương ngữ hoặc lỗi nhận dạng giọng nói.
Không suy luận thủ tục, field, dữ liệu định danh hoặc ý định mới.
Giữ nguyên tuyệt đối mọi placeholder dạng ⟦PROTECTED_n⟧.
Nếu một cụm có nhiều nghĩa hợp lý, giữ nguyên cụm đó và trả các lựa chọn trong ambiguities.
changed_spans dùng offset trên input đã được bảo vệ. Chỉ trả JSON đúng schema."""

_MODEL_ASSIST_HINT = re.compile(
    r"(?i)(?<!\w)(?:đăng\s+kí|tạm\s+(?!trú\b)\w+|thường\s+(?!trú\b)\w+|"
    r"trích\s+(?!lục\b)\w+|khai\s+(?!sinh\b)\w+|ko|hok|hem|dc|đc)(?!\w)"
)


class ProviderModelNormalizer:
    """Optional strict-schema tier backed by the existing provider abstraction."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        timeout_seconds: float = 12.0,
    ) -> None:
        self._provider = provider
        self._timeout_seconds = timeout_seconds

    def normalize(self, protected_text: str) -> ModelNormalizationCandidate:
        from vneguide.ai.providers.base import ProviderError, StructuredRequest

        try:
            payload = self._provider.generate_structured(
                StructuredRequest(
                    system_prompt=_MODEL_PROMPT,
                    user_prompt=protected_text,
                    json_schema=_MODEL_SCHEMA,
                    schema_name="vneguide_language_normalization",
                    timeout_seconds=self._timeout_seconds,
                )
            )
        except ProviderError as exc:
            raise ModelNormalizationUnavailable("model normalization failed") from exc
        if not isinstance(payload, Mapping):
            raise ModelNormalizationUnavailable("normalization model returned a non-object")
        normalized_text = payload.get("normalized_text")
        confidence = payload.get("confidence")
        changed_spans = payload.get("changed_spans")
        raw_ambiguities = payload.get("ambiguities")
        if not isinstance(normalized_text, str) or not normalized_text.strip():
            raise ModelNormalizationUnavailable("normalization model omitted normalized_text")
        if not isinstance(confidence, int | float) or isinstance(confidence, bool):
            raise ModelNormalizationUnavailable("normalization model returned invalid confidence")
        numeric_confidence = float(confidence)
        if not 0 <= numeric_confidence <= 1:
            raise ModelNormalizationUnavailable("normalization model returned invalid confidence")
        if not isinstance(changed_spans, list) or not isinstance(raw_ambiguities, list):
            raise ModelNormalizationUnavailable("normalization model returned invalid span arrays")
        _validate_model_changed_spans(changed_spans, protected_text, normalized_text)

        ambiguities: list[Ambiguity] = []
        for raw in raw_ambiguities:
            if not isinstance(raw, Mapping):
                raise ModelNormalizationUnavailable(
                    "normalization model returned invalid ambiguity"
                )
            phrase, options = raw.get("phrase"), raw.get("options")
            if not isinstance(phrase, str) or not isinstance(options, list):
                raise ModelNormalizationUnavailable(
                    "normalization model returned invalid ambiguity"
                )
            if any(not isinstance(option, str) or not option.strip() for option in options):
                raise ModelNormalizationUnavailable(
                    "normalization model returned invalid ambiguity options"
                )
            start = protected_text.casefold().find(phrase.casefold())
            if start < 0:
                raise ModelNormalizationUnavailable(
                    "normalization ambiguity is not grounded in input"
                )
            ambiguities.append(Ambiguity(phrase, tuple(options), start, start + len(phrase)))
        return ModelNormalizationCandidate(
            normalized_text=normalized_text,
            confidence=numeric_confidence,
            ambiguities=tuple(ambiguities),
        )


@dataclass(frozen=True, slots=True)
class _Rewrite:
    start: int
    end: int
    entry: GlossaryEntry


def _validate_model_changed_spans(
    changed_spans: list[Any],
    protected_text: str,
    normalized_text: str,
) -> None:
    occupied: list[tuple[int, int]] = []
    expected_keys = {"start", "end", "original", "normalized"}
    for span in changed_spans:
        if not isinstance(span, Mapping) or set(span) != expected_keys:
            raise ModelNormalizationUnavailable(
                "normalization model returned an invalid changed span"
            )
        start, end = span["start"], span["end"]
        original, normalized = span["original"], span["normalized"]
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or not 0 <= start < end <= len(protected_text)
            or not isinstance(original, str)
            or not isinstance(normalized, str)
            or original != protected_text[start:end]
            or original == normalized
            or _overlaps(start, end, occupied)
            or "⟦PROTECTED_" in original
        ):
            raise ModelNormalizationUnavailable(
                "normalization model returned an invalid changed span"
            )
        occupied.append((start, end))
    rebuilt = protected_text
    for span in sorted(changed_spans, key=lambda item: item["start"], reverse=True):
        rebuilt = rebuilt[: span["start"]] + span["normalized"] + rebuilt[span["end"] :]
    if rebuilt != normalized_text:
        raise ModelNormalizationUnavailable(
            "normalization model changed text outside declared spans"
        )


class LanguageNormalizer:
    """Apply reviewed rewrites first and a bounded optional model second."""

    def __init__(
        self,
        glossary: Glossary | None = None,
        *,
        model_normalizer: ModelNormalizer | None = None,
    ) -> None:
        self._glossary = glossary or default_glossary()
        self._model_normalizer = model_normalizer

    def normalize(
        self,
        text: str,
        *,
        source: InputSource = InputSource.TEXT,
        allow_model_assistance: bool = True,
    ) -> NormalizationResult:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        protected = detect_protected_spans(text)
        deterministic = self._deterministic(text, protected, source)
        if (
            deterministic.ambiguities
            or self._model_normalizer is None
            or not allow_model_assistance
            or not text.strip()
            or not _needs_model_assistance(deterministic)
        ):
            return deterministic

        protected_text, tokens = _replace_protected_with_tokens(deterministic)
        try:
            candidate = self._model_normalizer.normalize(protected_text)
        except (ModelNormalizationUnavailable, TypeError, ValueError):
            return deterministic
        if any(candidate.normalized_text.count(token) != 1 for token, _value in tokens):
            return deterministic
        restored = candidate.normalized_text
        for token, value in tokens:
            restored = restored.replace(token, value)
        if any(span.value not in restored for span in protected):
            return deterministic

        mappings = _diff_mappings(text, restored, protected)
        ambiguities = _restore_model_ambiguities(candidate, tokens, restored, mappings)
        return NormalizationResult(
            raw_text=text,
            normalized_text=restored,
            mappings=mappings,
            protected_spans=protected,
            confidence=candidate.confidence,
            ambiguities=ambiguities,
            input_source=source,
            model_assisted=True,
        )

    def _deterministic(
        self,
        text: str,
        protected: tuple[ProtectedSpan, ...],
        source: InputSource,
    ) -> NormalizationResult:
        ambiguities: list[Ambiguity] = []
        rewrites: list[_Rewrite] = []
        occupied: list[tuple[int, int]] = [(span.start, span.end) for span in protected]

        candidates: list[_Rewrite] = []
        for entry in self._glossary.entries:
            for match in entry.pattern.finditer(text):
                if _overlaps(match.start(), match.end(), occupied):
                    continue
                if entry.target is None:
                    ambiguities.append(
                        Ambiguity(
                            text[match.start() : match.end()],
                            entry.ambiguity_options,
                            match.start(),
                            match.end(),
                        )
                    )
                else:
                    candidates.append(_Rewrite(match.start(), match.end(), entry))

        for candidate in sorted(
            candidates,
            key=lambda item: (item.start, -(item.end - item.start)),
        ):
            if _overlaps(candidate.start, candidate.end, occupied):
                continue
            rewrites.append(candidate)
            occupied.append((candidate.start, candidate.end))

        mappings = _build_deterministic_mappings(text, protected, tuple(rewrites))
        normalized = "".join(mapping.normalized_text for mapping in mappings)
        confidence = 0.85 if rewrites else 1.0
        return NormalizationResult(
            raw_text=text,
            normalized_text=normalized,
            mappings=mappings,
            protected_spans=protected,
            confidence=confidence,
            ambiguities=tuple(sorted(ambiguities, key=lambda item: item.raw_start)),
            input_source=source,
        )


def _overlaps(start: int, end: int, occupied: Sequence[tuple[int, int]]) -> bool:
    return any(
        start < current_end and end > current_start for current_start, current_end in occupied
    )


def _needs_model_assistance(result: NormalizationResult) -> bool:
    if _MODEL_ASSIST_HINT.search(result.normalized_text):
        return True
    return result.input_source is InputSource.SPEECH and not result.changed_spans


def _match_case(raw: str, target: str) -> str:
    if raw.isupper():
        return target.upper()
    if raw[:1].isupper():
        return target[:1].upper() + target[1:]
    return target


def _build_deterministic_mappings(
    text: str,
    protected: tuple[ProtectedSpan, ...],
    rewrites: tuple[_Rewrite, ...],
) -> tuple[SpanMapping, ...]:
    protected_by_range = {(span.start, span.end): span for span in protected}
    rewrite_by_range = {(rewrite.start, rewrite.end): rewrite for rewrite in rewrites}
    boundaries = sorted(
        (*protected_by_range, *rewrite_by_range),
        key=lambda item: (item[0], -(item[1] - item[0])),
    )
    mappings: list[SpanMapping] = []
    raw_cursor = 0
    normalized_cursor = 0

    def append(raw_start: int, raw_end: int, normalized_text: str, **kwargs: Any) -> None:
        nonlocal normalized_cursor
        raw_text = text[raw_start:raw_end]
        mappings.append(
            SpanMapping(
                raw_start,
                raw_end,
                normalized_cursor,
                normalized_cursor + len(normalized_text),
                raw_text,
                normalized_text,
                **kwargs,
            )
        )
        normalized_cursor += len(normalized_text)

    for start, end in boundaries:
        if start < raw_cursor:
            continue
        if raw_cursor < start:
            append(raw_cursor, start, text[raw_cursor:start])
        protected_span = protected_by_range.get((start, end))
        rewrite = rewrite_by_range.get((start, end))
        if protected_span is not None:
            append(start, end, protected_span.value, protected_kind=protected_span.kind)
        elif rewrite is not None and rewrite.entry.target is not None:
            append(
                start,
                end,
                _match_case(text[start:end], rewrite.entry.target),
                rule_id=rewrite.entry.rule_id,
            )
        raw_cursor = end
    if raw_cursor < len(text):
        append(raw_cursor, len(text), text[raw_cursor:])
    return tuple(mappings)


def _replace_protected_with_tokens(
    result: NormalizationResult,
) -> tuple[str, tuple[tuple[str, str], ...]]:
    parts: list[str] = []
    tokens: list[tuple[str, str]] = []
    for mapping in result.mappings:
        if mapping.protected_kind is None:
            parts.append(mapping.normalized_text)
            continue
        token = f"⟦PROTECTED_{len(tokens)}⟧"
        tokens.append((token, mapping.normalized_text))
        parts.append(token)
    return "".join(parts), tuple(tokens)


def _diff_mappings(
    raw_text: str,
    normalized_text: str,
    protected: tuple[ProtectedSpan, ...],
) -> tuple[SpanMapping, ...]:
    matcher = difflib.SequenceMatcher(a=raw_text, b=normalized_text, autojunk=False)
    mappings: list[SpanMapping] = []
    for tag, raw_start, raw_end, normalized_start, normalized_end in matcher.get_opcodes():
        protected_kind = next(
            (
                span.kind
                for span in protected
                if raw_start == span.start and raw_end == span.end and tag == "equal"
            ),
            None,
        )
        mappings.append(
            SpanMapping(
                raw_start,
                raw_end,
                normalized_start,
                normalized_end,
                raw_text[raw_start:raw_end],
                normalized_text[normalized_start:normalized_end],
                rule_id=None if tag == "equal" else "model.assisted",
                protected_kind=protected_kind,
            )
        )
    return tuple(mappings)


def _restore_model_ambiguities(
    candidate: ModelNormalizationCandidate,
    tokens: tuple[tuple[str, str], ...],
    restored: str,
    mappings: tuple[SpanMapping, ...],
) -> tuple[Ambiguity, ...]:
    if not candidate.ambiguities:
        return ()
    raw_text = "".join(mapping.raw_text for mapping in mappings)
    result = NormalizationResult(
        raw_text=raw_text,
        normalized_text=restored,
        mappings=mappings,
        protected_spans=(),
        confidence=candidate.confidence,
        ambiguities=(),
        input_source=InputSource.SPEECH,
        model_assisted=True,
    )
    restored_ambiguities: list[Ambiguity] = []
    for ambiguity in candidate.ambiguities:
        phrase = ambiguity.phrase
        for token, value in tokens:
            phrase = phrase.replace(token, value)
        start = restored.casefold().find(phrase.casefold())
        raw_phrase = result.raw_text_for(phrase)
        if start < 0 or raw_phrase is None:
            continue
        raw_start = raw_text.find(raw_phrase)
        if raw_start < 0:
            continue
        restored_ambiguities.append(
            Ambiguity(raw_phrase, ambiguity.options, raw_start, raw_start + len(raw_phrase))
        )
    return tuple(restored_ambiguities)


__all__ = [
    "LanguageNormalizer",
    "ModelNormalizationUnavailable",
    "ModelNormalizer",
    "ProviderModelNormalizer",
]
