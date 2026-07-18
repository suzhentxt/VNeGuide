"""LangChain ChatModel adapter for the GLM-5.2 HTTP gateway.

The gateway at ``VNEGUIDE_LITELLM_BASE_URL`` speaks the OpenAI Chat Completions
API (verified to support ``tools`` / ``tool_choice`` for native function calling).
This adapter wraps :class:`langchain_openai.ChatOpenAI` so the deep-agent layer
gets ``bind_tools`` / ``with_structured_output`` while reusing the same gateway
and credentials as :class:`LiteLLMChatCompletionsProvider`.

The gateway is HTTP-only for the trusted dev environment, so the underlying
``httpx`` client is configured with ``verify=False`` when
``allow_insecure_http`` is set.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from .base import ProviderConfigurationError

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from ..config import LLMConfig


def build_chat_model(config: LLMConfig) -> BaseChatModel:
    """Build a LangChain ChatModel pointed at the configured GLM gateway."""

    from langchain_openai import ChatOpenAI

    if config.provider == "mock":
        return _build_fake_model()
    if config.provider not in {"litellm", "openai"}:
        raise ProviderConfigurationError(
            f"LangChain chat model does not support provider {config.provider!r}"
        )
    base_url = config.litellm_base_url if config.provider == "litellm" else None
    model = config.model
    api_key = config.api_key
    if model is None or (config.provider == "litellm" and base_url is None):
        raise ProviderConfigurationError(
            "Chat model requires VNEGUIDE_MODEL and VNEGUIDE_LITELLM_BASE_URL"
        )

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": 0,
        "timeout": 60,
        "max_retries": 1,
    }
    if api_key is not None:
        kwargs["api_key"] = api_key
    if base_url is not None:
        kwargs["base_url"] = _chat_completions_base_url(base_url)
        if config.litellm_allow_insecure_http and base_url.startswith("http://"):
            kwargs["http_client"] = httpx.Client(verify=False, timeout=60)
    return ChatOpenAI(**kwargs)


def _build_fake_model() -> BaseChatModel:
    from .fake_chat import FakeChatModel

    return FakeChatModel(responses=[])


def _chat_completions_base_url(base_url: str) -> str:
    """Return the base URL for the OpenAI client (without the /v1/... path).

    ``ChatOpenAI`` appends ``/chat/completions`` itself, so we pass only the
    scheme + host + port + ``/v1``.
    """

    trimmed = base_url.strip().rstrip("/")
    if trimmed.endswith("/v1"):
        return trimmed
    return f"{trimmed}/v1"


__all__ = ["build_chat_model"]
