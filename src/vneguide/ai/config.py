"""Lazy environment configuration for LLM providers."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .providers import (
    LiteLLMChatCompletionsProvider,
    LLMProvider,
    MockLLMProvider,
    OpenAIResponsesProvider,
    ProviderConfigurationError,
)

_MAX_ENV_FILE_BYTES = 64_000
_ENV_FILE_KEYS = frozenset(
    {
        "VNEGUIDE_API_KEY",
        "VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP",
        "VNEGUIDE_LITELLM_API_KEY",
        "VNEGUIDE_LITELLM_BASE_URL",
        "VNEGUIDE_LITELLM_DISABLE_THINKING",
        "VNEGUIDE_LANGUAGE_MODEL_ASSISTED",
        "VNEGUIDE_LLM_PROVIDER",
        "VNEGUIDE_MODEL",
    }
)


@dataclass(frozen=True)
class LLMConfig:
    """Provider selection without exposing the API key in representations."""

    provider: str
    model: str | None
    api_key: str | None = field(repr=False)
    litellm_base_url: str | None = None
    litellm_allow_insecure_http: bool = False
    litellm_disable_thinking: bool = True
    language_model_assisted: bool = False


def load_llm_config(
    environ: Mapping[str, str] | None = None,
    *,
    env_file: str | Path | None = None,
) -> LLMConfig:
    """Read LLM settings lazily, optionally overlaying an explicit ``.env`` file."""

    source: dict[str, str] = {}
    if env_file is not None:
        source.update(_read_env_file(Path(env_file)))
    source.update(os.environ if environ is None else environ)
    provider = source.get("VNEGUIDE_LLM_PROVIDER", "mock").strip().lower() or "mock"
    model = source.get("VNEGUIDE_MODEL", "").strip() or None
    generic_api_key = source.get("VNEGUIDE_API_KEY", "").strip() or None
    if provider == "litellm":
        api_key = source.get("VNEGUIDE_LITELLM_API_KEY", "").strip() or None
    else:
        api_key = generic_api_key
    base_url = source.get("VNEGUIDE_LITELLM_BASE_URL", "").strip() or None
    allow_insecure_http = _read_boolean(
        source,
        "VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP",
        default=False,
    )
    disable_thinking = _read_boolean(
        source,
        "VNEGUIDE_LITELLM_DISABLE_THINKING",
        default=True,
    )
    language_model_assisted = _read_boolean(
        source,
        "VNEGUIDE_LANGUAGE_MODEL_ASSISTED",
        default=False,
    )
    return LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        litellm_base_url=base_url,
        litellm_allow_insecure_http=allow_insecure_http,
        litellm_disable_thinking=disable_thinking,
        language_model_assisted=language_model_assisted,
    )


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
    if config.provider == "litellm":
        if config.model is None or config.litellm_base_url is None:
            raise ProviderConfigurationError(
                "LiteLLM provider requires VNEGUIDE_MODEL and VNEGUIDE_LITELLM_BASE_URL"
            )
        return LiteLLMChatCompletionsProvider(
            api_key=config.api_key,
            base_url=config.litellm_base_url,
            model=config.model,
            allow_insecure_http=config.litellm_allow_insecure_http,
            disable_thinking=config.litellm_disable_thinking,
        )
    raise ProviderConfigurationError(f"Unknown LLM provider: {config.provider!r}")


def _read_boolean(source: Mapping[str, str], name: str, *, default: bool) -> bool:
    value = source.get(name)
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ProviderConfigurationError(f"{name} must be a boolean value")


def _read_env_file(path: Path) -> dict[str, str]:
    try:
        if path.stat().st_size > _MAX_ENV_FILE_BYTES:
            raise ProviderConfigurationError("LLM env file exceeds the safe size limit")
        text = path.read_text(encoding="utf-8")
    except ProviderConfigurationError:
        raise
    except (OSError, UnicodeError):
        raise ProviderConfigurationError("LLM env file could not be read") from None

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if line_number == 1:
            line = line.lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ProviderConfigurationError(f"LLM env file has an invalid line {line_number}")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if key not in _ENV_FILE_KEYS:
            continue
        if key in values:
            raise ProviderConfigurationError(f"LLM env file repeats {key}")
        value = raw_value.strip()
        if value[:1] in {'"', "'"}:
            quote = value[0]
            if len(value) < 2 or value[-1] != quote:
                raise ProviderConfigurationError(
                    f"LLM env file has an invalid quoted value on line {line_number}"
                )
            value = value[1:-1]
        values[key] = value
    return values


__all__ = ["LLMConfig", "build_llm_provider", "load_llm_config"]
