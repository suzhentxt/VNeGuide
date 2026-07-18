"""Qwen multimodal OCR adapter for the configured LiteLLM gateway."""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable, Mapping, Sequence
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from vneguide.ai.config import LLMConfig

from .errors import OcrBackendError
from .models import OcrBlock, PreparedPage

_SUPPORTED_MODEL = "Qwen/Qwen3.5-9B"
_CHAT_COMPLETIONS_PATH = "/v1/chat/completions"
_MAX_RESPONSE_BYTES = 2_000_000
_MAX_BLOCKS_PER_PAGE = 100
_RETRYABLE_HTTP_STATUSES = {408, 409, 425, 429}

_OCR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["blocks"],
    "properties": {
        "blocks": {
            "type": "array",
            "maxItems": _MAX_BLOCKS_PER_PAGE,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type", "bbox", "angle", "content"],
                "properties": {
                    "type": {"type": "string", "enum": ["text", "table", "image"]},
                    "bbox": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "angle": {"type": ["integer", "null"], "enum": [0, 90, 180, 270, None]},
                    "content": {"type": ["string", "null"], "maxLength": 4000},
                },
            },
        }
    },
}

_SYSTEM_PROMPT = """You are a document OCR engine, not an administrative decision maker.
Transcribe only text visibly present in the supplied image. Preserve Vietnamese diacritics.
Scan the complete page from top to bottom and return every visible line, including all fields below
the title; returning only a title or header is incomplete. Use one reading-order text block per
visible line with normalized [x1,y1,x2,y2] coordinates. Never complete, correct, infer, or invent a
name, identifier, address, date, legal fact, fee, or requirement. Use the required JSON schema and
no prose."""


class QwenVisionBackend:
    """Extract layout text with Qwen/Qwen3.5-9B via an OpenAI-compatible endpoint."""

    def __init__(
        self,
        config: LLMConfig,
        *,
        timeout_seconds: float = 300,
        opener: Callable[..., Any] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if config.provider != "litellm":
            raise ValueError("Qwen OCR requires the litellm provider")
        if config.model != _SUPPORTED_MODEL:
            raise ValueError(f"Qwen OCR requires {_SUPPORTED_MODEL}")
        if config.litellm_base_url is None:
            raise ValueError("Qwen OCR requires VNEGUIDE_LITELLM_BASE_URL")
        if config.api_key is not None:
            _validate_api_key(config.api_key)
        if timeout_seconds <= 0:
            raise ValueError("Qwen OCR timeout must be positive")
        self._api_url = _chat_completions_url(
            config.litellm_base_url,
            allow_insecure_http=config.litellm_allow_insecure_http,
        )
        self._model = config.model
        self._api_key = config.api_key
        self._disable_thinking = config.litellm_disable_thinking
        self._timeout_seconds = timeout_seconds
        self._opener = opener
        self._sleeper = sleeper

    def extract(self, pages: Sequence[PreparedPage]) -> tuple[OcrBlock, ...]:
        blocks: list[OcrBlock] = []
        for page in pages:
            payload = self._request_page(page)
            blocks.extend(self._convert_blocks(payload, page_number=page.page_number))
        return tuple(blocks)

    def _request_page(self, page: PreparedPage) -> object:
        encoded = base64.b64encode(page.jpeg_content).decode("ascii")
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "OCR the entire document page exactly. Continue through the last "
                                "visible line; do not return only the header."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                        },
                    ],
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "vneguide_ocr_page", "schema": _OCR_SCHEMA, "strict": True},
            },
            "stream": False,
            "max_tokens": 4096,
        }
        if self._disable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = Request(self._api_url, data=body, headers=headers, method="POST")
        for attempt in range(2):
            try:
                return self._decode_response(self._send(request))
            except OcrBackendError as exc:
                if attempt == 0 and exc.code in {
                    "provider_retryable_http_error",
                    "provider_timeout",
                    "provider_unavailable",
                }:
                    self._sleeper(1.0)
                    continue
                raise
        raise AssertionError("bounded Qwen OCR retry loop did not terminate")

    def _send(self, request: Request) -> bytes:
        opener = self._opener or _open_without_redirects
        response: Any | None = None
        try:
            response = opener(request, timeout=self._timeout_seconds)
            status_code = _response_status(response)
            if status_code is not None and not 200 <= status_code < 300:
                raise _http_error(status_code)
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if not isinstance(raw, bytes) or len(raw) > _MAX_RESPONSE_BYTES:
                raise OcrBackendError("invalid_model_output", "Qwen OCR trả output quá lớn.")
            return raw
        except OcrBackendError:
            raise
        except HTTPError as exc:
            raise _http_error(exc.code) from None
        except (TimeoutError, URLError):
            raise OcrBackendError("provider_timeout", "Qwen OCR gateway quá hạn.") from None
        except (HTTPException, OSError):
            raise OcrBackendError(
                "provider_unavailable", "Qwen OCR gateway không sẵn sàng."
            ) from None
        finally:
            if response is not None:
                close = getattr(response, "close", None)
                if callable(close):
                    close()

    @staticmethod
    def _decode_response(raw: bytes) -> object:
        try:
            response = json.loads(
                raw.decode("utf-8"),
                parse_constant=_reject_json_constant,
                object_pairs_hook=_reject_duplicate_pairs,
            )
            choices = response["choices"]
            choice = choices[0]
            if choice.get("finish_reason") != "stop":
                raise KeyError("finish_reason")
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("content")
            return json.loads(
                content,
                parse_constant=_reject_json_constant,
                object_pairs_hook=_reject_duplicate_pairs,
            )
        except (IndexError, KeyError, TypeError, UnicodeError, ValueError):
            raise OcrBackendError(
                "invalid_model_output", "Qwen OCR trả output không hợp lệ."
            ) from None

    @staticmethod
    def _convert_blocks(payload: object, *, page_number: int) -> list[OcrBlock]:
        if not isinstance(payload, Mapping):
            raise OcrBackendError("invalid_model_output", "Qwen OCR trả object không hợp lệ.")
        raw_blocks = payload.get("blocks")
        if not isinstance(raw_blocks, list) or len(raw_blocks) > _MAX_BLOCKS_PER_PAGE:
            raise OcrBackendError("invalid_model_output", "Qwen OCR trả blocks không hợp lệ.")
        converted: list[OcrBlock] = []
        for raw in raw_blocks:
            if not isinstance(raw, Mapping):
                continue
            block_type = raw.get("type")
            bbox = raw.get("bbox")
            angle = raw.get("angle")
            content = raw.get("content")
            if block_type not in {"text", "table", "image"}:
                continue
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue
            try:
                normalized_bbox = tuple(float(item) for item in bbox)
            except (TypeError, ValueError):
                continue
            if any(not 0.0 <= coordinate <= 1.0 for coordinate in normalized_bbox):
                continue
            if normalized_bbox[0] > normalized_bbox[2] or normalized_bbox[1] > normalized_bbox[3]:
                continue
            normalized_angle = angle if type(angle) is int and angle in {0, 90, 180, 270} else None
            converted.append(
                OcrBlock(
                    block_type=block_type,
                    bbox=(
                        normalized_bbox[0],
                        normalized_bbox[1],
                        normalized_bbox[2],
                        normalized_bbox[3],
                    ),
                    angle=normalized_angle,
                    content=content if isinstance(content, str) else None,
                    page_number=page_number,
                )
            )
        return converted


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


def _chat_completions_url(base_url: str, *, allow_insecure_http: bool) -> str:
    if any(ord(character) < 32 or ord(character) == 127 for character in base_url):
        raise ValueError("Qwen OCR base URL is invalid")
    try:
        parsed = urlparse(base_url.strip())
        _ = parsed.port
    except (AttributeError, ValueError):
        raise ValueError("Qwen OCR base URL is invalid") from None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Qwen OCR base URL must use HTTP or HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Qwen OCR base URL must not contain credentials")
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("Qwen OCR base URL must contain only scheme, host and port")
    if parsed.scheme == "http" and not allow_insecure_http:
        raise ValueError("Qwen OCR HTTP requires explicit insecure opt-in")
    return f"{parsed.scheme}://{parsed.netloc}{_CHAT_COMPLETIONS_PATH}"


def _response_status(response: Any) -> int | None:
    status = getattr(response, "status", None)
    return status if isinstance(status, int) else None


def _http_error(status_code: int) -> OcrBackendError:
    if status_code in {401, 403}:
        return OcrBackendError("provider_auth_failed", "Qwen OCR gateway từ chối xác thực.")
    if status_code in _RETRYABLE_HTTP_STATUSES or status_code >= 500:
        return OcrBackendError(
            "provider_retryable_http_error", "Qwen OCR gateway tạm thời không sẵn sàng."
        )
    return OcrBackendError("provider_request_rejected", "Qwen OCR gateway từ chối request.")


def _validate_api_key(api_key: str) -> None:
    if (
        not api_key
        or not api_key.isascii()
        or any(not 33 <= ord(character) <= 126 for character in api_key)
    ):
        raise ValueError("Qwen OCR API key format is invalid")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Unsupported JSON constant: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    decoded: dict[str, Any] = {}
    for key, value in pairs:
        if key in decoded:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        decoded[key] = value
    return decoded


__all__ = ["QwenVisionBackend"]
