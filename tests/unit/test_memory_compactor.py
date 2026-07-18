from __future__ import annotations

import pytest

from vneguide.ai import MemoryCompactor, MockLLMProvider, ProviderError
from vneguide.domain import ChatMessage, MessageRole


def _turns(*pairs: tuple[str, str]) -> tuple[ChatMessage, ...]:
    messages: list[ChatMessage] = []
    for user, assistant in pairs:
        messages.append(ChatMessage(MessageRole.USER, user))
        messages.append(ChatMessage(MessageRole.ASSISTANT, assistant))
    return tuple(messages)


def test_compact_produces_summary_from_turns() -> None:
    provider = MockLLMProvider([{"summary": "Công dân tên Hậu, đang hỏi về giấy khai sinh."}])
    compactor = MemoryCompactor(provider)
    result = compactor.compact("", _turns(("tôi tên Hậu", "Dạ em chào anh Hậu.")))

    assert result.succeeded is True
    assert result.summary is not None
    assert "Hậu" in result.summary
    call = provider.calls[0]
    assert "tôi tên Hậu" in call.system_prompt
    assert "Tóm tắt hiện tại" in call.system_prompt


def test_compact_integrates_existing_summary() -> None:
    provider = MockLLMProvider([{"summary": "Anh Hậu, đã chọn thủ tục khai sinh."}])
    compactor = MemoryCompactor(provider)
    result = compactor.compact(
        "Công dân tên Hậu.",
        _turns(("tôi muốn bản sao khai sinh", "Dạ, em hỗ trợ anh ạ.")),
    )

    assert result.succeeded is True
    call = provider.calls[0]
    assert "Công dân tên Hậu." in call.system_prompt


def test_compact_returns_none_on_provider_failure() -> None:
    provider = MockLLMProvider([ProviderError("gateway down", retryable=True)])
    compactor = MemoryCompactor(provider)
    result = compactor.compact("", _turns(("tôi tên Hậu", "Dạ em chào anh.")))

    assert result.succeeded is False
    assert result.summary is None


def test_compact_returns_none_on_malformed_payload() -> None:
    provider = MockLLMProvider([{"summary": ""}])
    compactor = MemoryCompactor(provider)
    result = compactor.compact("", _turns(("tôi tên Hậu", "Dạ em chào anh.")))

    assert result.succeeded is False
    assert result.summary is None


def test_compact_empty_turns_returns_existing_summary() -> None:
    compactor = MemoryCompactor(MockLLMProvider([]))
    result = compactor.compact("đã có tóm tắt", ())

    assert result.succeeded is True
    assert result.summary == "đã có tóm tắt"


def test_compact_rejects_non_chatmessage_entries() -> None:
    compactor = MemoryCompactor(MockLLMProvider([]))
    with pytest.raises(ValueError):
        compactor.compact("", ("không phải ChatMessage",))  # type: ignore[arg-type]
