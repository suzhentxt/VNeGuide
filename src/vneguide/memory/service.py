"""Privacy-bounded port around Mem0's ``add`` and ``search`` workflow."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

_AGENT_ID = "vneguide"
_CATEGORY = "accessibility_preference"
_RECALL_QUERY = "Sở thích hỗ trợ khi sử dụng VNeGuide"
_MAX_RECALLED = 3
_MAX_MEMORY_CHARS = 160

_PREFERENCE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\b(?:trả lời|nói|viết)\s+(?:thật\s+)?(?:ngắn|ngắn gọn)\b", re.IGNORECASE),
        "Người dùng muốn câu trả lời ngắn gọn.",
    ),
    (
        re.compile(
            r"\b(?:nói|viết|giải thích|trả lời)\s+(?:thật\s+)?(?:đơn giản|dễ hiểu)\b",
            re.IGNORECASE,
        ),
        "Người dùng muốn cách diễn đạt đơn giản, dễ hiểu.",
    ),
    (
        re.compile(r"\b(?:hướng dẫn|nói|làm)\s+(?:cho tôi\s+)?từng bước\b", re.IGNORECASE),
        "Người dùng muốn được hướng dẫn từng bước một.",
    ),
)


class Mem0Client(Protocol):
    """The small Mem0 surface VNeGuide depends on."""

    def add(
        self,
        messages: str | list[dict[str, str]],
        *,
        user_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        infer: bool = True,
    ) -> Any: ...

    def search(
        self,
        query: str,
        *,
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> Any: ...


@dataclass(frozen=True, slots=True)
class MemoryScope:
    """Opaque Mem0 entity identifiers; never contains citizen data."""

    user_id: str
    run_id: str
    agent_id: str = _AGENT_ID

    def __post_init__(self) -> None:
        for name, value in (
            ("user_id", self.user_id),
            ("run_id", self.run_id),
            ("agent_id", self.agent_id),
        ):
            if not value or len(value) > 128 or not value.isascii():
                raise ValueError(f"{name} must be a short opaque ASCII identifier")


class LongTermMemory:
    """Best-effort long-term memory restricted to explicit support preferences."""

    def __init__(self, client: Mem0Client) -> None:
        self._client = client

    def recall(self, scope: MemoryScope) -> tuple[str, ...]:
        """Recall bounded preferences without sending the current user message."""

        try:
            response = self._client.search(
                _RECALL_QUERY,
                top_k=_MAX_RECALLED,
                filters={
                    "user_id": scope.user_id,
                    "agent_id": scope.agent_id,
                    "category": _CATEGORY,
                },
            )
        except Exception:
            return ()
        if not isinstance(response, Mapping):
            return ()
        results = response.get("results")
        if not isinstance(results, list):
            return ()
        memories: list[str] = []
        for item in results[:_MAX_RECALLED]:
            if not isinstance(item, Mapping):
                continue
            memory = item.get("memory")
            if not isinstance(memory, str):
                continue
            normalized = memory.strip()[:_MAX_MEMORY_CHARS]
            if normalized in _allowed_preferences() and normalized not in memories:
                memories.append(normalized)
        return tuple(memories)

    def remember(self, scope: MemoryScope, user_message: str) -> bool:
        """Store only a normalized allow-listed preference, never raw transcript."""

        preference = _preference_from_message(user_message)
        if preference is None:
            return False
        try:
            self._client.add(
                preference,
                user_id=scope.user_id,
                agent_id=scope.agent_id,
                run_id=scope.run_id,
                metadata={"category": _CATEGORY, "source": "explicit_user_preference"},
                infer=False,
            )
        except Exception:
            return False
        return True


def _preference_from_message(message: str) -> str | None:
    if not isinstance(message, str) or len(message) > 4_000:
        return None
    for pattern, normalized in _PREFERENCE_RULES:
        if pattern.search(message):
            return normalized
    return None


def _allowed_preferences() -> frozenset[str]:
    return frozenset(value for _pattern, value in _PREFERENCE_RULES)


__all__ = ["LongTermMemory", "Mem0Client", "MemoryScope"]
