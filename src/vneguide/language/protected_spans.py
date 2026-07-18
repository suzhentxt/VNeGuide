"""Detect identity-bearing spans before any linguistic rewrite is attempted."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import ProtectedKind, ProtectedSpan


@dataclass(frozen=True, slots=True)
class _Pattern:
    kind: ProtectedKind
    regex: re.Pattern[str]
    value_group: str | int = 0


_NAME_TOKEN = r"(?!(?:CCCD|CMND|SĐT|SDT)\b)[A-ZÀ-ỴĐ][A-Za-zÀ-ỹĐđ]*"
_VIETNAMESE_NAME = rf"{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{1,5}}"

_PATTERNS = (
    _Pattern(ProtectedKind.PROCEDURE_CODE, re.compile(r"(?<!\d)\d{1,3}\.\d{6}(?!\d)")),
    _Pattern(
        ProtectedKind.CASE_CODE,
        re.compile(
            r"(?i)(?:mã\s+(?:hồ\s+sơ|biên\s+nhận)|hồ\s+sơ)\s*[:#-]?\s*"
            r"(?P<value>[A-Z0-9][A-Z0-9._/-]{4,})"
        ),
        "value",
    ),
    _Pattern(
        ProtectedKind.PHONE_NUMBER,
        re.compile(r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9,10}(?!\d)"),
    ),
    _Pattern(ProtectedKind.CCCD, re.compile(r"(?<!\d)\d{12}(?!\d)")),
    _Pattern(
        ProtectedKind.DATE_OF_BIRTH,
        re.compile(r"(?<!\d)(?:\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2})(?!\d)"),
    ),
    _Pattern(
        ProtectedKind.DATE_OF_BIRTH,
        re.compile(r"(?i)ngày\s+\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}"),
    ),
    _Pattern(
        ProtectedKind.FULL_NAME,
        re.compile(
            rf"(?i:(?:tôi|tui|mình|em|anh|chị)\s+(?:tên|là)\s+)"
            rf"(?P<value>{_VIETNAMESE_NAME})"
        ),
        "value",
    ),
    _Pattern(
        ProtectedKind.ADDRESS,
        re.compile(
            r"(?i)(?:địa\s+chỉ|cư\s+trú\s+tại|ở\s+tại)\s+"
            r"(?P<value>[^,;.!?]{3,120}?)(?=\s+(?:để|và\s+tôi|tôi\s+muốn|tôi\s+cần)|[,;.!?]|$)"
        ),
        "value",
    ),
)


def detect_protected_spans(text: str) -> tuple[ProtectedSpan, ...]:
    """Return deterministic, non-overlapping identity spans sorted by offset."""

    candidates: list[ProtectedSpan] = []
    for pattern in _PATTERNS:
        for match in pattern.regex.finditer(text):
            start, end = match.span(pattern.value_group)
            candidates.append(ProtectedSpan(pattern.kind, start, end, text[start:end]))

    # Prefer an earlier and longer match when recognizers overlap (for example a
    # labeled case code containing digits). No later stage may split the winner.
    selected: list[ProtectedSpan] = []
    for candidate in sorted(candidates, key=lambda item: (item.start, -(item.end - item.start))):
        if any(
            candidate.start < current.end and candidate.end > current.start for current in selected
        ):
            continue
        selected.append(candidate)
    return tuple(sorted(selected, key=lambda item: item.start))


__all__ = ["detect_protected_spans"]
