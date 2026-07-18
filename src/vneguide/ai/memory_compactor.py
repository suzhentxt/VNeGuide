"""LLM-driven compaction of older conversation turns into a running summary.

When the message log grows past its bounded window, the session folds the
oldest verbatim turns into ``memory_summary`` via this compactor. The summary
is the only durable home for older context; the recent window stays verbatim.
Compaction never blocks a turn: on any provider failure or malformed payload
it returns ``None`` and the caller keeps the messages untouched, retrying on a
later turn.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from vneguide.ai.prompts import build_memory_summary_prompt
from vneguide.ai.providers.base import (
    LLMProvider,
    ProviderConfigurationError,
    ProviderError,
    ProviderRefusal,
    ProviderTimeout,
    StructuredRequest,
)
from vneguide.domain import ChatMessage

_SUMMARY_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
}

_MAX_SUMMARY_CHARS = 1_200
_MAX_OLD_TURNS = 24


@dataclass(frozen=True, slots=True)
class CompactionResult:
    """A compacted summary, or a signal that compaction should be skipped."""

    summary: str | None
    succeeded: bool


class MemoryCompactor:
    """Fold older conversation turns into a short running summary."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        timeout_seconds: float = 20.0,
    ) -> None:
        if (
            type(timeout_seconds) not in (int, float)
            or not math.isfinite(float(timeout_seconds))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive number")
        self._provider = provider
        self._timeout_seconds = timeout_seconds

    def compact(
        self,
        existing_summary: str,
        old_turns: tuple[ChatMessage, ...],
    ) -> CompactionResult:
        """Return a compacted summary, or ``succeeded=False`` to skip compaction."""

        if not isinstance(existing_summary, str):
            raise ValueError("existing_summary must be a string")
        if not isinstance(old_turns, tuple):
            raise ValueError("old_turns must be a tuple")
        if any(not isinstance(turn, ChatMessage) for turn in old_turns):
            raise ValueError("old_turns must contain ChatMessage values")
        if not old_turns:
            return CompactionResult(summary=existing_summary, succeeded=True)
        bounded = old_turns[-_MAX_OLD_TURNS:]
        system_prompt = build_memory_summary_prompt(
            existing_summary=existing_summary,
            old_turns=bounded,
        )
        request = StructuredRequest(
            system_prompt=system_prompt,
            user_prompt="Hãy gộp các lượt trên vào tóm tắt theo quy tắc đã nêu.",
            json_schema=_SUMMARY_SCHEMA,
            schema_name="vneguide_memory_summary",
            timeout_seconds=self._timeout_seconds,
        )
        try:
            raw = self._provider.generate_structured(request)
        except (ProviderConfigurationError, ProviderRefusal, ProviderTimeout, ProviderError):
            return CompactionResult(summary=None, succeeded=False)
        summary = _decode_summary(raw)
        if summary is None:
            return CompactionResult(summary=None, succeeded=False)
        return CompactionResult(summary=summary[:_MAX_SUMMARY_CHARS], succeeded=True)


def _decode_summary(raw: object) -> str | None:
    if not isinstance(raw, Mapping):
        return None
    summary = raw.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return None
    return summary.strip()


__all__ = ["CompactionResult", "MemoryCompactor"]


# Validate JSON encoding eagerly so a bad schema never reaches the provider.
try:
    json.dumps(dict(_SUMMARY_SCHEMA), ensure_ascii=False)
except (TypeError, ValueError) as _exc:  # pragma: no cover - schema is a literal
    raise RuntimeError("memory summary schema is not JSON-serializable") from _exc
