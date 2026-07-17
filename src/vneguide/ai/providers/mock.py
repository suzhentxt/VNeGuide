"""Deterministic provider used by unit and integration tests."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from .base import ProviderConfigurationError, StructuredRequest


class MockLLMProvider:
    """Return queued values or raise queued exceptions in call order."""

    def __init__(self, responses: Iterable[object] = ()) -> None:
        self._responses: deque[object] = deque(responses)
        self.calls: list[StructuredRequest] = []

    @property
    def remaining(self) -> int:
        """Number of scripted outcomes that have not been consumed."""

        return len(self._responses)

    def enqueue(self, result: object) -> None:
        """Append an outcome for a later call."""

        self._responses.append(result)

    def generate_structured(self, request: StructuredRequest) -> object:
        self.calls.append(request)
        if not self._responses:
            raise ProviderConfigurationError("Mock provider has no scripted response")

        result = self._responses.popleft()
        if isinstance(result, Exception):
            raise result
        return result
