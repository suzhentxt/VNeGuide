"""Tests for the LangChain chat model adapter (Phase 0).

Verifies that :func:`build_chat_model` produces a usable ``BaseChatModel`` for
the GLM gateway, a ``FakeChatModel`` for the mock provider, and raises for
unsupported providers.
"""

from __future__ import annotations

import pytest
from langchain_core.language_models import BaseChatModel

from vneguide.ai.config import LLMConfig
from vneguide.ai.providers import ProviderConfigurationError
from vneguide.ai.providers.fake_chat import FakeChatModel
from vneguide.ai.providers.langchain_chat import (
    _chat_completions_base_url,
    build_chat_model,
)


def test_mock_provider_returns_fake_chat_model() -> None:
    config = LLMConfig(provider="mock", model=None, api_key=None)
    model = build_chat_model(config)
    assert isinstance(model, FakeChatModel)


def test_litellm_provider_returns_chat_openai() -> None:
    config = LLMConfig(
        provider="litellm",
        model="zai-org/GLM-5.2",
        api_key="test-key",
        litellm_base_url="http://localhost:9207",
        litellm_allow_insecure_http=True,
    )
    model = build_chat_model(config)
    assert isinstance(model, BaseChatModel)
    assert getattr(model, "model_name", None) == "zai-org/GLM-5.2"
    assert getattr(model, "temperature", 1) == 0


def test_openai_provider_returns_chat_openai() -> None:
    config = LLMConfig(
        provider="openai",
        model="gpt-4o",
        api_key="test-key",
    )
    model = build_chat_model(config)
    assert isinstance(model, BaseChatModel)
    assert getattr(model, "model_name", None) == "gpt-4o"


def test_unsupported_provider_raises() -> None:
    config = LLMConfig(provider="anthropic", model="claude-3", api_key="x")
    with pytest.raises(ProviderConfigurationError):
        build_chat_model(config)


def test_litellm_without_model_raises() -> None:
    config = LLMConfig(
        provider="litellm",
        model=None,
        api_key="x",
        litellm_base_url="http://localhost:9207",
    )
    with pytest.raises(ProviderConfigurationError):
        build_chat_model(config)


def test_litellm_without_base_url_raises() -> None:
    config = LLMConfig(
        provider="litellm",
        model="zai-org/GLM-5.2",
        api_key="x",
        litellm_base_url=None,
    )
    with pytest.raises(ProviderConfigurationError):
        build_chat_model(config)


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("http://localhost:9207", "http://localhost:9207/v1"),
        ("http://localhost:9207/", "http://localhost:9207/v1"),
        ("http://localhost:9207/v1", "http://localhost:9207/v1"),
        ("http://localhost:9207/v1/", "http://localhost:9207/v1"),
        ("https://api.example.com", "https://api.example.com/v1"),
    ],
)
def test_chat_completions_base_url(base_url: str, expected: str) -> None:
    assert _chat_completions_base_url(base_url) == expected


def test_insecure_http_configures_httpx_client() -> None:
    import httpx

    config = LLMConfig(
        provider="litellm",
        model="zai-org/GLM-5.2",
        api_key="test-key",
        litellm_base_url="http://171.244.195.83:9207",
        litellm_allow_insecure_http=True,
    )
    model = build_chat_model(config)
    http_client = getattr(model, "http_client", None)
    assert http_client is not None
    assert isinstance(http_client, httpx.Client)
