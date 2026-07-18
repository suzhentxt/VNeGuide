"""Deterministic mapping from OCR layout blocks to reviewed CT01 fields."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from vneguide.domain import JSONValue

from .models import OcrBlock, OcrCandidate, OcrMappingResult

_TITLE_ANCHOR = "tờ khai thay đổi thông tin cư trú"
_FORM_ANCHOR = "ct01"
_DOCUMENT_THRESHOLD = 0.90
_CANDIDATE_THRESHOLD = 0.65
_LOW_CONFIDENCE_THRESHOLD = 0.85


@dataclass(frozen=True, slots=True)
class _FieldRule:
    field_id: str
    labels: tuple[str, ...]
    value_pattern: re.Pattern[str]
    group: int = 1


_FIELD_RULES = (
    _FieldRule(
        "applicant_full_name",
        ("họ, chữ đệm và tên", "họ và tên"),
        re.compile(r"(?:họ,?\s*chữ\s*đệm\s*và\s*tên|họ\s*và\s*tên)\s*[:.]?\s*(.+)", re.I),
    ),
    _FieldRule(
        "applicant_date_of_birth",
        ("ngày, tháng, năm sinh", "ngày sinh"),
        re.compile(
            r"(?:ngày,?\s*tháng,?\s*năm\s*sinh|ngày\s*sinh)\s*[:.]?\s*"
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            re.I,
        ),
    ),
    _FieldRule(
        "applicant_personal_id",
        ("số định danh cá nhân",),
        re.compile(r"số\s*định\s*danh\s*cá\s*nhân\s*[:.]?\s*(\d{12})", re.I),
    ),
    _FieldRule(
        "temporary_address",
        ("đăng ký tạm trú tại", "địa chỉ tạm trú"),
        re.compile(r"(?:đăng\s*ký\s*tạm\s*trú\s*tại|địa\s*chỉ\s*tạm\s*trú)\s*[:.]?\s*(.+)", re.I),
    ),
)


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def _phrase_score(lines: Sequence[str], phrase: str) -> float:
    normalized_phrase = _normalize(phrase)
    scores: list[float] = []
    for line in lines:
        normalized_line = _normalize(line)
        if normalized_phrase in normalized_line:
            return 1.0
        scores.append(SequenceMatcher(None, normalized_phrase, normalized_line).ratio())
    return max(scores, default=0.0)


def _canonical_date(value: str) -> str | None:
    parts = re.split(r"[/-]", value)
    if len(parts) != 3:
        return None
    try:
        day, month, year = (int(part) for part in parts)
        from datetime import date

        return date(year, month, day).isoformat()
    except ValueError:
        return None


class CT01TemplateMapper:
    """Map only visible CT01 values; never derive administrative facts."""

    def map(
        self,
        blocks: Sequence[OcrBlock],
        *,
        validate_value: Callable[[str, JSONValue], None],
    ) -> OcrMappingResult:
        text_blocks = [
            block
            for block in blocks
            if block.block_type == "text" and block.content is not None and block.content.strip()
        ]
        ordered = sorted(
            text_blocks,
            key=lambda item: (item.page_number, item.bbox[1], item.bbox[0]),
        )
        lines = [block.content.strip() for block in ordered if block.content is not None]
        title_score = _phrase_score(lines, _TITLE_ANCHOR)
        form_score = _phrase_score(lines, _FORM_ANCHOR)
        document_confidence = (title_score + form_score) / 2
        if min(title_score, form_score) < _DOCUMENT_THRESHOLD:
            return OcrMappingResult(
                document_type="other",
                document_confidence=document_confidence,
                warnings=("wrong_document_type",),
            )

        candidates: list[OcrCandidate] = []
        warnings: list[str] = []
        for rule in _FIELD_RULES:
            candidate = self._extract_rule(
                rule,
                ordered,
                document_confidence=document_confidence,
                validate_value=validate_value,
            )
            if candidate is None:
                continue
            if candidate.confidence < _CANDIDATE_THRESHOLD:
                warnings.append(f"discarded_low_confidence:{rule.field_id}")
                continue
            if candidate.confidence < _LOW_CONFIDENCE_THRESHOLD:
                warnings.append(f"low_confidence:{rule.field_id}")
            candidates.append(candidate)
        return OcrMappingResult(
            document_type="CT01",
            document_confidence=document_confidence,
            candidates=tuple(candidates),
            warnings=tuple(warnings),
        )

    def _extract_rule(
        self,
        rule: _FieldRule,
        blocks: Sequence[OcrBlock],
        *,
        document_confidence: float,
        validate_value: Callable[[str, JSONValue], None],
    ) -> OcrCandidate | None:
        best: tuple[float, OcrBlock, str] | None = None
        for block in blocks:
            assert block.content is not None
            match = rule.value_pattern.search(block.content)
            if match is not None:
                label_score = max(_phrase_score((block.content,), label) for label in rule.labels)
                extracted_value = match.group(rule.group).strip(" .;,-")
                if best is None or label_score > best[0]:
                    best = (label_score, block, extracted_value)
        if best is None:
            return None
        label_score, block, raw_value = best
        value: JSONValue = raw_value
        if rule.field_id == "applicant_date_of_birth":
            canonical = _canonical_date(raw_value)
            if canonical is None:
                return None
            value = canonical
        try:
            validate_value(rule.field_id, value)
        except (TypeError, ValueError):
            return None
        rotation_penalty = 0.16 if block.angle not in {None, 0} else 0.0
        confidence = max(
            0.0,
            min(1.0, 0.40 * document_confidence + 0.35 * label_score + 0.25) - rotation_penalty,
        )
        assert block.content is not None
        return OcrCandidate(
            field_id=rule.field_id,
            suggested_value=value,
            confidence=confidence,
            evidence=block.content[:500],
        )


__all__ = ["CT01TemplateMapper"]
