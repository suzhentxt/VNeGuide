"""Lazy environment configuration for LLM providers."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from .providers import (
    LLMProvider,
    MockLLMProvider,
    OpenAIResponsesProvider,
    ProviderConfigurationError,
)


@dataclass(frozen=True)
class LLMConfig:
    """Provider selection without exposing the API key in representations."""

    provider: str
    model: str | None
    api_key: str | None = field(repr=False)


def load_llm_config(environ: Mapping[str, str] | None = None) -> LLMConfig:
    """Read LLM settings when called, never at module import time."""

    source = os.environ if environ is None else environ
    provider = source.get("VNEGUIDE_LLM_PROVIDER", "mock").strip().lower() or "mock"
    model = source.get("VNEGUIDE_MODEL", "").strip() or None
    api_key = source.get("VNEGUIDE_API_KEY", "").strip() or None
    return LLMConfig(provider=provider, model=model, api_key=api_key)


def build_llm_provider(config: LLMConfig, *, mock_responses: Iterable[object] = ()) -> LLMProvider:
    """Build the configured provider without reading environment state again."""

    if config.provider == "mock":
        return MockLLMProvider(mock_responses)
    if config.provider == "openai":
        if config.model is None or config.api_key is None:
            raise ProviderConfigurationError(
                "OpenAI provider requires VNEGUIDE_MODEL and VNEGUIDE_API_KEY"
            )
        return OpenAIResponsesProvider(api_key=config.api_key, model=config.model)
    raise ProviderConfigurationError(f"Unknown LLM provider: {config.provider!r}")


__all__ = ["LLMConfig", "build_llm_provider", "load_llm_config"]
