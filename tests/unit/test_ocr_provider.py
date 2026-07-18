from __future__ import annotations

import json
from urllib.request import Request

import pytest

from vneguide.ai.config import LLMConfig
from vneguide.ocr import OcrBackendError, PreparedPage, QwenVisionBackend


class FakeResponse:
    def __init__(self, payload: bytes, *, status: int = 200) -> None:
        self._payload = payload
        self.status = status
        self.closed = False

    def read(self, _limit: int) -> bytes:
        return self._payload

    def close(self) -> None:
        self.closed = True


def _config(*, allow_http: bool = True, model: str = "Qwen/Qwen3.5-9B") -> LLMConfig:
    return LLMConfig(
        provider="litellm",
        model=model,
        api_key="synthetic-key",
        litellm_base_url="http://127.0.0.1:9207",
        litellm_allow_insecure_http=allow_http,
        litellm_disable_thinking=True,
    )


def test_qwen_backend_sends_multimodal_schema_and_converts_blocks() -> None:
    requests: list[Request] = []
    content = json.dumps(
        {
            "blocks": [
                {
                    "type": "text",
                    "bbox": [0.1, 0.2, 0.8, 0.3],
                    "angle": 0,
                    "content": "Mẫu CT01",
                }
            ]
        },
        ensure_ascii=False,
    )
    response = FakeResponse(
        json.dumps(
            {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}
        ).encode()
    )

    def opener(request: Request, *, timeout: float) -> FakeResponse:
        assert timeout == 12
        requests.append(request)
        return response

    backend = QwenVisionBackend(_config(), timeout_seconds=12, opener=opener)
    result = backend.extract((PreparedPage(1, b"synthetic-jpeg", 100, 100),))

    assert len(result) == 1
    assert result[0].content == "Mẫu CT01"
    request_data = requests[0].data
    assert isinstance(request_data, bytes)
    payload = json.loads(request_data.decode())
    assert payload["model"] == "Qwen/Qwen3.5-9B"
    assert payload["messages"][1]["content"][1]["type"] == "image_url"
    assert payload["messages"][1]["content"][1]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,"
    )
    assert payload["response_format"]["type"] == "json_schema"
    assert response.closed is True


def test_qwen_backend_rejects_another_model() -> None:
    with pytest.raises(ValueError, match="Qwen/Qwen3.5-9B"):
        QwenVisionBackend(_config(model="another-model"))


def test_qwen_backend_rejects_unapproved_plain_http() -> None:
    with pytest.raises(ValueError, match="explicit insecure opt-in"):
        QwenVisionBackend(_config(allow_http=False))


def test_qwen_backend_rejects_unsafe_api_key() -> None:
    config = LLMConfig(
        provider="litellm",
        model="Qwen/Qwen3.5-9B",
        api_key="unsafe\nheader",
        litellm_base_url="https://127.0.0.1:9207",
    )
    with pytest.raises(ValueError, match="API key"):
        QwenVisionBackend(config)


def test_malformed_model_response_fails_to_manual_fallback() -> None:
    def opener(_request: Request, *, timeout: float) -> FakeResponse:
        return FakeResponse(b"not-json")

    backend = QwenVisionBackend(_config(), opener=opener, sleeper=lambda _seconds: None)
    with pytest.raises(OcrBackendError) as caught:
        backend.extract((PreparedPage(1, b"synthetic-jpeg", 100, 100),))
    assert caught.value.code == "invalid_model_output"


def test_duplicate_json_keys_fail_closed() -> None:
    duplicate_content = '{"blocks":[],"blocks":[]}'
    raw = json.dumps(
        {"choices": [{"finish_reason": "stop", "message": {"content": duplicate_content}}]}
    ).encode()
    with pytest.raises(OcrBackendError) as caught:
        QwenVisionBackend._decode_response(raw)
    assert caught.value.code == "invalid_model_output"


def test_invalid_blocks_are_discarded() -> None:
    converted = QwenVisionBackend._convert_blocks(
        {
            "blocks": [
                {"type": "text", "bbox": [2, 0, 3, 1], "angle": 0, "content": "bad"},
                {"type": "image", "bbox": [0, 0, 1, 1], "angle": None, "content": None},
            ]
        },
        page_number=1,
    )
    assert len(converted) == 1
    assert converted[0].block_type == "image"


def test_retryable_gateway_error_is_retried_once() -> None:
    attempts = 0
    valid_content = json.dumps({"blocks": []})
    valid_response = json.dumps(
        {"choices": [{"finish_reason": "stop", "message": {"content": valid_content}}]}
    ).encode()

    def opener(_request: Request, *, timeout: float) -> FakeResponse:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return FakeResponse(b"temporary", status=503)
        return FakeResponse(valid_response)

    backend = QwenVisionBackend(_config(), opener=opener, sleeper=lambda _seconds: None)
    result = backend.extract((PreparedPage(1, b"synthetic-jpeg", 100, 100),))

    assert result == ()
    assert attempts == 2
