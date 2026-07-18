from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pytest

from vneguide.ocr import OcrBackendError, OpenAIDocumentValidationBackend, PreparedPage


class Response(BytesIO):
    status = 200


def completed(payload: dict[str, object]) -> bytes:
    return json.dumps(
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(payload)}],
                }
            ],
        }
    ).encode()


def test_openai_vision_request_is_non_storing_and_returns_no_raw_text() -> None:
    captured: dict[str, Any] = {}
    codes = (
        "document_type_match",
        "readable_content",
        "dwelling_location_present",
        "dwelling_relationship_present",
    )

    def opener(request: Any, *, timeout: float) -> Response:
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response(
            completed(
                {
                    "checks": {code: {"result": "pass", "confidence": 0.95} for code in codes},
                    "overall_confidence": 0.95,
                }
            )
        )

    backend = OpenAIDocumentValidationBackend(
        api_key="synthetic-key", model="gpt-5.5", timeout_seconds=12, opener=opener
    )
    result = backend.assess("legal_dwelling", (PreparedPage(1, b"jpeg", 10, 10),))
    payload = captured["payload"]
    assert payload["store"] is False
    assert payload["model"] == "gpt-5.5"
    assert payload["input"][1]["content"][1]["type"] == "input_image"
    assert result.overall_confidence == 0.95
    assert not any(hasattr(check, "content") for check in result.checks)


def test_provider_rejects_invalid_credentials_and_output() -> None:
    with pytest.raises(ValueError, match="API key"):
        OpenAIDocumentValidationBackend(api_key="")
    backend = OpenAIDocumentValidationBackend(
        api_key="synthetic-key", opener=lambda *_args, **_kwargs: Response(b"{}")
    )
    with pytest.raises(OcrBackendError) as caught:
        backend.assess("minor_consent", (PreparedPage(1, b"jpeg", 10, 10),))
    assert caught.value.code == "invalid_model_output"
