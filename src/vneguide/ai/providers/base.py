"""Provider-neutral contracts for structured LLM calls."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class StructuredRequest:
    """A single request whose response must conform to ``json_schema``."""

    system_prompt: str
    user_prompt: str
    json_schema: Mapping[str, Any]
    schema_name: str
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.schema_name.strip():
            raise ValueError("schema_name must not be empty")
        if (
            type(self.timeout_seconds) not in (int, float)
            or not math.isfinite(float(self.timeout_seconds))
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive number")


class ProviderError(RuntimeError):
    """Base error raised by an LLM provider.

    ``retryable`` lets the extractor apply one bounded retry without knowing
    transport-specific status codes.
    """

    default_retryable = False

    def __init__(
        self,
        message: str,
        *,
        retryable: bool | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = self.default_retryable if retryable is None else retryable
        self.status_code = status_code


class ProviderTimeout(ProviderError):
    """The provider did not complete within the configured deadline."""

    default_retryable = True


class ProviderRefusal(ProviderError):
    """The model refused to answer; retrying the same request is unsafe."""


class ProviderConfigurationError(ProviderError):
    """Provider configuration is missing or invalid."""


@runtime_checkable
class LLMProvider(Protocol):
    """Interface consumed by the structured extractor."""

    def generate_structured(self, request: StructuredRequest) -> object:
        """Return a provider value or raise a typed ``ProviderError``."""
