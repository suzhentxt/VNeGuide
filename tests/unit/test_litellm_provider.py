"""Unit tests for the LiteLLM Chat Completions adapter."""

from __future__ import annotations

import json
import unittest
from email.message import Message
from http.client import IncompleteRead
from typing import cast
from urllib.error import HTTPError
from urllib.request import Request as HTTPRequest

from vneguide.ai.providers import (
    LiteLLMChatCompletionsProvider,
    ProviderConfigurationError,
    ProviderError,
    ProviderRefusal,
    ProviderTimeout,
    StructuredRequest,
)
from vneguide.ai.providers.litellm import _NoRedirectHandler


class _FakeHTTPResponse:
    def __init__(self, payload: object, status: int = 200) -> None:
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]

    def close(self) -> None:
        self.closed = True


def _request() -> StructuredRequest:
    return StructuredRequest(
        system_prompt="system",
        user_prompt="user",
        json_schema={
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
        schema_name="test_schema",
        timeout_seconds=4.0,
    )


def _completion(
    content: object = '{"ok":true}',
    *,
    finish_reason: object = "stop",
    message_extra: dict[str, object] | None = None,
) -> dict[str, object]:
    message: dict[str, object] = {"role": "assistant", "content": content}
    if message_extra:
        message.update(message_extra)
    return {
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": message,
            }
        ]
    }


class LiteLLMChatCompletionsProviderTests(unittest.TestCase):
    def test_sends_strict_schema_disables_thinking_and_decodes_content(self) -> None:
        captured: dict[str, object] = {}
        response = _FakeHTTPResponse(_completion())

        def opener(request: object, *, timeout: float) -> _FakeHTTPResponse:
            captured["request"] = request
            captured["timeout"] = timeout
            return response

        provider = LiteLLMChatCompletionsProvider(
            api_key="test-key",
            base_url="http://127.0.0.1:9207/",
            model="test-model",
            allow_insecure_http=True,
            opener=opener,
        )

        result = provider.generate_structured(_request())

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["timeout"], 4.0)
        http_request = cast(HTTPRequest, captured["request"])
        self.assertEqual(http_request.full_url, "http://127.0.0.1:9207/v1/chat/completions")
        self.assertEqual(http_request.get_header("Authorization"), "Bearer test-key")
        sent = json.loads(cast(bytes, http_request.data).decode("utf-8"))
        self.assertEqual(sent["model"], "test-model")
        self.assertEqual(sent["temperature"], 0)
        self.assertFalse(sent["stream"])
        self.assertFalse(sent["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(sent["response_format"]["type"], "json_schema")
        self.assertTrue(sent["response_format"]["json_schema"]["strict"])
        self.assertNotIn("test-key", json.dumps(sent))
        self.assertTrue(response.closed)

    def test_omits_auth_and_thinking_extension_when_disabled(self) -> None:
        captured: dict[str, object] = {}

        def opener(request: object, *, timeout: float) -> _FakeHTTPResponse:
            captured["request"] = request
            return _FakeHTTPResponse(_completion())

        provider = LiteLLMChatCompletionsProvider(
            base_url="https://gateway.example",
            model="test-model",
            disable_thinking=False,
            opener=opener,
        )
        provider.generate_structured(_request())

        http_request = cast(HTTPRequest, captured["request"])
        self.assertIsNone(http_request.get_header("Authorization"))
        sent = json.loads(cast(bytes, http_request.data).decode("utf-8"))
        self.assertNotIn("chat_template_kwargs", sent)

    def test_recovers_only_a_leading_thinking_prefix_before_strict_json(self) -> None:
        for content in (
            '<think>Phân tích nội bộ.</think>\n{"ok":true}',
            'Phân tích nội bộ.</think> {"ok":true}',
        ):
            with self.subTest(content=content):
                provider = LiteLLMChatCompletionsProvider(
                    base_url="https://gateway.example",
                    model="test-model",
                    opener=lambda request, timeout, value=content: _FakeHTTPResponse(
                        _completion(value)
                    ),
                )
                self.assertEqual(provider.generate_structured(_request()), {"ok": True})

        untouched = LiteLLMChatCompletionsProvider(
            base_url="https://gateway.example",
            model="test-model",
            opener=lambda request, timeout: _FakeHTTPResponse(
                _completion('{"note":"<think>literal</think>"}')
            ),
        )
        self.assertEqual(
            untouched.generate_structured(_request()),
            {"note": "<think>literal</think>"},
        )

    def test_thinking_recovery_keeps_duplicate_and_trailing_content_rejected(self) -> None:
        malformed_contents = (
            '<think>chưa đóng {"ok":true}',
            '<think>x</think>{"ok":true,"ok":false}',
            '<think>x</think>{"ok":true} trailing prose',
        )
        for content in malformed_contents:
            with self.subTest(content=content):
                provider = LiteLLMChatCompletionsProvider(
                    base_url="https://gateway.example",
                    model="test-model",
                    opener=lambda request, timeout, value=content: _FakeHTTPResponse(
                        _completion(value)
                    ),
                )
                with self.assertRaises(ProviderError):
                    provider.generate_structured(_request())

    def test_rejects_unsafe_urls_and_http_without_explicit_opt_in(self) -> None:
        invalid_urls = (
            "http://gateway.example",
            "ftp://gateway.example",
            "https://user:pass@gateway.example",
            "https://gateway.example/custom/path",
            "https://gateway.example?token=value",
            "https://gateway.example#fragment",
            "https://gateway.example:bad",
            "https://gateway.example\nunsafe",
        )
        for base_url in invalid_urls:
            with self.subTest(base_url=base_url), self.assertRaises(ProviderConfigurationError):
                LiteLLMChatCompletionsProvider(base_url=base_url, model="test-model")

    def test_rejects_header_unsafe_key_without_echoing_it(self) -> None:
        unsafe_key = "test-key\nDO-NOT-LEAK"
        with self.assertRaises(ProviderConfigurationError) as context:
            LiteLLMChatCompletionsProvider(
                api_key=unsafe_key,
                base_url="https://gateway.example",
                model="test-model",
            )
        self.assertNotIn("DO-NOT-LEAK", str(context.exception))

    def test_maps_refusal_length_and_malformed_content_to_typed_errors(self) -> None:
        cases: tuple[tuple[object, type[ProviderError], bool], ...] = (
            (_completion(finish_reason="length"), ProviderError, True),
            (_completion(finish_reason="content_filter"), ProviderRefusal, False),
            (_completion(message_extra={"refusal": "no"}), ProviderRefusal, False),
            (_completion("not-json"), ProviderError, True),
            (_completion("[1,2]"), ProviderError, True),
            (_completion('{"ok":true,"ok":false}'), ProviderError, True),
            ({"choices": []}, ProviderError, True),
        )
        for response_payload, error_type, retryable in cases:
            with self.subTest(payload=response_payload):
                provider = LiteLLMChatCompletionsProvider(
                    base_url="https://gateway.example",
                    model="test-model",
                    opener=lambda request, timeout, payload=response_payload: _FakeHTTPResponse(
                        payload
                    ),
                )
                with self.assertRaises(error_type) as context:
                    provider.generate_structured(_request())
                self.assertEqual(context.exception.retryable, retryable)

    def test_wraps_timeout_http_errors_truncation_and_oversized_response(self) -> None:
        timeout_provider = LiteLLMChatCompletionsProvider(
            base_url="https://gateway.example",
            model="test-model",
            opener=lambda request, timeout: (_ for _ in ()).throw(TimeoutError()),
        )
        with self.assertRaises(ProviderTimeout):
            timeout_provider.generate_structured(_request())

        for status, error_type, retryable in (
            (401, ProviderConfigurationError, False),
            (422, ProviderError, False),
            (429, ProviderError, True),
            (503, ProviderError, True),
        ):
            with self.subTest(status=status):
                provider = LiteLLMChatCompletionsProvider(
                    base_url="https://gateway.example",
                    model="test-model",
                    opener=lambda request, timeout, code=status: (_ for _ in ()).throw(
                        HTTPError(request.full_url, code, "error", Message(), None)
                    ),
                )
                with self.assertRaises(error_type) as context:
                    provider.generate_structured(_request())
                self.assertEqual(context.exception.retryable, retryable)

        class TruncatedResponse:
            status = 200

            def read(self, size: int = -1) -> bytes:
                raise IncompleteRead(b"{", 10)

            def close(self) -> None:
                pass

        truncated = LiteLLMChatCompletionsProvider(
            base_url="https://gateway.example",
            model="test-model",
            opener=lambda request, timeout: TruncatedResponse(),
        )
        with self.assertRaises(ProviderError):
            truncated.generate_structured(_request())

        class OversizedResponse:
            status = 200

            def read(self, size: int = -1) -> bytes:
                return b"x" * size

            def close(self) -> None:
                pass

        oversized = LiteLLMChatCompletionsProvider(
            base_url="https://gateway.example",
            model="test-model",
            opener=lambda request, timeout: OversizedResponse(),
        )
        with self.assertRaises(ProviderError):
            oversized.generate_structured(_request())

    def test_default_transport_disables_redirects(self) -> None:
        handler = _NoRedirectHandler()
        redirected = handler.redirect_request(
            None,
            None,
            302,
            "Found",
            {},
            "https://example.com/steal-key",
        )
        self.assertIsNone(redirected)


if __name__ == "__main__":
    unittest.main()
