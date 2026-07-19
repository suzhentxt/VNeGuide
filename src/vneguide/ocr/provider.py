"""OpenAI Responses vision adapter for bounded document validation."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Mapping, Sequence
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .errors import OcrBackendError
from .models import DocumentCheck, DocumentKind, ModelAssessment, PreparedPage

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
_MAX_RESPONSE_BYTES = 1_000_000
_RETRYABLE_HTTP_STATUSES = {408, 409, 425, 429}
_CHECK_CODES: dict[DocumentKind, tuple[str, ...]] = {
    "legal_dwelling": ("name_valid", "date_valid"),
    "minor_consent": ("name_valid", "date_valid"),
}

_SYSTEM_PROMPT = """You validate synthetic Vietnamese administrative demo documents.
Inspect only visible content. Never infer identity, legal ownership, signature authenticity, legal
validity, notarization, or government approval. Do not transcribe or return names, identifiers,
addresses, dates, signatures, or any other raw document text. Return only the required check enums
and confidence numbers. Use uncertain whenever the image is incomplete, blurry, ambiguous, or a
check cannot be established from visible content."""

_KIND_PROMPTS: dict[DocumentKind, str] = {
    "legal_dwelling": (
        "Check whether this document visibly contains a person's full name that looks valid "
        "(present, non-placeholder, plausible Vietnamese name) and a date that looks valid "
        "(proper format, plausible, not obviously fabricated). Do not transcribe the actual "
        "name or date values, and do not decide whether the claims are legally true."
    ),
    "minor_consent": (
        "Check whether this document visibly contains a person's full name that looks valid "
        "(present, non-placeholder, plausible Vietnamese name) and a date that looks valid "
        "(proper format, plausible, not obviously fabricated). Do not transcribe the actual "
        "name or date values, and do not verify identities or signatures."
    ),
}


class OpenAIDocumentValidationBackend:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.5",
        timeout_seconds: float = 60,
        api_url: str = OPENAI_RESPONSES_URL,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        if not api_key or not api_key.isascii() or any(not 33 <= ord(c) <= 126 for c in api_key):
            raise ValueError("OpenAI OCR API key format is invalid")
        if not model.strip():
            raise ValueError("OpenAI OCR model is required")
        if api_url != OPENAI_RESPONSES_URL:
            raise ValueError("OpenAI OCR endpoint must be the official Responses API")
        if timeout_seconds <= 0:
            raise ValueError("OpenAI OCR timeout must be positive")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._api_url = api_url
        self._opener = opener

    def assess(
        self,
        document_kind: DocumentKind,
        pages: Sequence[PreparedPage],
    ) -> ModelAssessment:
        if document_kind not in _CHECK_CODES:
            raise ValueError("Unsupported OCR document kind")
        if not pages:
            raise ValueError("OCR requires at least one prepared page")
        payload = self._request_payload(document_kind, pages)
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = Request(
            self._api_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        raw = self._send(request)
        return self._convert_assessment(document_kind, self._decode_response(raw))

    def _request_payload(
        self,
        document_kind: DocumentKind,
        pages: Sequence[PreparedPage],
    ) -> dict[str, Any]:
        content: list[dict[str, str]] = [
            {"type": "input_text", "text": _KIND_PROMPTS[document_kind]}
        ]
        for page in pages:
            encoded = base64.b64encode(page.jpeg_content).decode("ascii")
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{encoded}",
                    "detail": "high",
                }
            )
        codes = _CHECK_CODES[document_kind]
        check_schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["result", "confidence"],
            "properties": {
                "result": {"type": "string", "enum": ["pass", "uncertain", "fail"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
        }
        return {
            "model": self._model,
            "input": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": f"vneguide_{document_kind}_validation",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["checks", "overall_confidence"],
                        "properties": {
                            "checks": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": list(codes),
                                "properties": {code: check_schema for code in codes},
                            },
                            "overall_confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                        },
                    },
                }
            },
            "store": False,
        }

    def _send(self, request: Request) -> bytes:
        opener = self._opener or _open_without_redirects
        response: Any | None = None
        try:
            response = opener(request, timeout=self._timeout_seconds)
            status = _response_status(response)
            if status is not None and not 200 <= status < 300:
                raise _http_error(status)
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if not isinstance(raw, bytes) or len(raw) > _MAX_RESPONSE_BYTES:
                raise OcrBackendError("invalid_model_output", "OCR trả kết quả không hợp lệ.")
            return raw
        except OcrBackendError:
            raise
        except HTTPError as exc:
            raise _http_error(exc.code) from None
        except (TimeoutError, URLError):
            raise OcrBackendError("provider_timeout", "OCR phản hồi quá thời gian.") from None
        except (HTTPException, OSError):
            raise OcrBackendError("provider_unavailable", "OCR chưa sẵn sàng.") from None
        finally:
            if response is not None:
                close = getattr(response, "close", None)
                if callable(close):
                    close()

    @staticmethod
    def _decode_response(raw: bytes) -> Mapping[str, Any]:
        try:
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, Mapping) or payload.get("status") != "completed":
                raise ValueError("response status")
            output = payload.get("output")
            if not isinstance(output, list):
                raise ValueError("output")
            parts: list[str] = []
            for item in output:
                if not isinstance(item, Mapping) or item.get("type") != "message":
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if isinstance(part, Mapping) and part.get("type") == "refusal":
                        raise OcrBackendError("provider_refusal", "OCR từ chối tài liệu.")
                    if isinstance(part, Mapping) and part.get("type") == "output_text":
                        text = part.get("text")
                        if isinstance(text, str):
                            parts.append(text)
            structured = json.loads("".join(parts))
            if not isinstance(structured, Mapping):
                raise ValueError("structured output")
            return structured
        except OcrBackendError:
            raise
        except (UnicodeError, ValueError, TypeError):
            raise OcrBackendError("invalid_model_output", "OCR trả kết quả không hợp lệ.") from None

    @staticmethod
    def _convert_assessment(
        document_kind: DocumentKind,
        payload: Mapping[str, Any],
    ) -> ModelAssessment:
        try:
            raw_checks = payload["checks"]
            overall = float(payload["overall_confidence"])
            if not isinstance(raw_checks, Mapping):
                raise TypeError("checks")
            checks = []
            for code in _CHECK_CODES[document_kind]:
                item = raw_checks[code]
                if not isinstance(item, Mapping):
                    raise TypeError(code)
                result = item["result"]
                confidence = float(item["confidence"])
                if result not in {"pass", "uncertain", "fail"}:
                    raise ValueError("result")
                checks.append(DocumentCheck(code, result, confidence))
            return ModelAssessment(tuple(checks), overall)
        except (KeyError, TypeError, ValueError):
            raise OcrBackendError("invalid_model_output", "OCR trả kết quả không hợp lệ.") from None


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        return None


def _open_without_redirects(request: Request, *, timeout: float) -> Any:
    return build_opener(_NoRedirectHandler()).open(request, timeout=timeout)


def _response_status(response: Any) -> int | None:
    status = getattr(response, "status", None)
    return status if isinstance(status, int) else None


def _http_error(status: int) -> OcrBackendError:
    if status in {401, 403}:
        return OcrBackendError("provider_auth_failed", "OCR không thể xác thực.")
    if status in _RETRYABLE_HTTP_STATUSES or status >= 500:
        return OcrBackendError("provider_unavailable", "OCR chưa sẵn sàng.")
    return OcrBackendError("provider_request_rejected", "OCR từ chối yêu cầu.")


__all__ = ["OPENAI_RESPONSES_URL", "OpenAIDocumentValidationBackend"]
