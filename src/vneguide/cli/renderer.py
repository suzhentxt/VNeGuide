"""Render shared turn results for a text terminal."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from enum import Enum
from typing import Any

_SENSITIVE_KEY_PARTS = (
    "cccd",
    "citizen_id",
    "identification_number",
    "national_id",
    "personal_id",
)


def _read(value: object, field: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(field, default)
    return getattr(value, field, default)


def _is_sensitive_key(key: object) -> bool:
    normalized = str(key).casefold().replace("-", "_").replace(" ", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _mask(value: object) -> str:
    text = str(value)
    visible = text[-4:] if len(text) > 4 else ""
    return f"{'*' * max(4, len(text) - len(visible))}{visible}"


def to_safe_data(value: Any) -> Any:
    """Convert supported model values to JSON-safe, privacy-aware data."""

    if isinstance(value, Enum):
        return to_safe_data(value.value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return to_safe_data(dataclasses.asdict(value))
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return to_safe_data(model_dump(mode="json"))
    if isinstance(value, Mapping):
        return {
            str(key): _mask(item) if _is_sensitive_key(key) and item else to_safe_data(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [to_safe_data(item) for item in value]
    return str(value)


def _json(value: Any) -> str:
    return json.dumps(to_safe_data(value), ensure_ascii=False, indent=2, sort_keys=True)


def _list_or_empty(value: Any) -> str:
    safe_value = to_safe_data(value)
    if not safe_value:
        return "(không có)"
    if isinstance(safe_value, list):
        return "\n".join(f"- {item}" for item in safe_value)
    return str(safe_value)


def _render_issues(issues: Any) -> str:
    if not issues:
        return "(không có)"

    lines: list[str] = []
    for issue in issues:
        field = _read(
            issue,
            "field",
            _read(issue, "field_path", _read(issue, "field_id", "toàn hồ sơ")),
        )
        severity = _read(issue, "severity", "issue")
        reason = _read(issue, "reason", _read(issue, "message", "Cần kiểm tra lại."))
        fix = _read(issue, "suggested_fix", _read(issue, "suggestion", None))
        line = f"- [{severity}] {field}: {reason}"
        if fix:
            line += f" Cách sửa: {fix}"
        lines.append(line)
    return "\n".join(lines)


def render_turn_result(result: object, *, include_reply: bool = True) -> str:
    """Render the documented ``TurnResult`` fields without owning their models."""

    sections: list[str] = []
    reply = _read(result, "reply", "")
    if include_reply and reply:
        sections.append(f"Trợ lý: {reply}")

    procedure = to_safe_data(_read(result, "procedure_type", "chưa xác định"))
    next_action = to_safe_data(_read(result, "next_action", "chưa xác định"))
    sections.extend(
        [
            "--- Trạng thái hồ sơ ---",
            f"Thủ tục: {procedure}",
            "Dữ liệu trích xuất:\n" + _json(_read(result, "extracted_fields", {})),
            "Hồ sơ nháp:\n" + _json(_read(result, "draft", {})),
            "Trường còn thiếu:\n" + _list_or_empty(_read(result, "missing_fields", [])),
            "Lỗi kiểm tra:\n" + _render_issues(_read(result, "validation_issues", [])),
            "Nguồn tham khảo:\n" + _list_or_empty(_read(result, "source_ids", [])),
            f"Bước tiếp theo: {next_action}",
        ]
    )
    return "\n".join(sections)
