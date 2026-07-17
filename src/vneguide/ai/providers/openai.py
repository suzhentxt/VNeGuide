"""Standard-library adapter for OpenAI's Responses REST API."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .base import (
    ProviderConfigurationError,
    ProviderError,
    ProviderRefusal,
    ProviderTimeout,
    StructuredRequest,
)

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
_SCHEMA_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_RETRYABLE_HTTP_STATUSES = {408, 409, 425, 429}
_MAX_RESPONSE_BYTES = 2_000_000


class OpenAIResponsesProvider:
    """Send strict JSON-schema requests to ``POST /v1/responses``."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        api_url: str = OPENAI_RESPONSES_URL,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        if (
            not isinstance(api_key, str)
            or not api_key
            or not api_key.isascii()
            or any(not 33 <= ord(character) <= 126 for character in api_key)
        ):
            raise ProviderConfigurationError("OpenAI API key format is invalid")
        if not isinstance(model, str) or not model.strip():
            raise ProviderConfigurationError("OpenAI model is required")
        if not isinstance(api_url, str):
            raise ProviderConfigurationError("OpenAI Responses API URL is invalid")
        _validate_api_url(api_url)

        self._api_key = api_key
        self._model = model
        self._api_url = api_url
        self._opener = opener

    def generate_structured(self, request: StructuredRequest) -> Mapping[str, Any]:
        if not _SCHEMA_NAME_PATTERN.fullmatch(request.schema_name):
            raise ProviderConfigurationError(
                "schema_name must contain 1-64 letters, digits, underscores, or dashes"
            )

        payload = {
            "model": self._model,
            "input": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": request.schema_name,
                    "schema": dict(request.json_schema),
                    "strict": True,
                }
            },
            "store": False,
        }
        try:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError):
            raise ProviderConfigurationError(
                "OpenAI request payload could not be encoded"
            ) from None
        http_request = Request(
            self._api_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        raw_response = self._send(http_request, timeout_seconds=request.timeout_seconds)
        return self._decode_response(raw_response)

    def _send(self, request: Request, *, timeout_seconds: float) -> bytes:
        opener = self._opener or _open_without_redirects
        response: Any | None = None
        try:
            response = opener(request, timeout=timeout_seconds)
            status_code = _response_status(response)
            if status_code is not None and not 200 <= status_code < 300:
                raise _http_error(status_code)
            raw_response = response.read(_MAX_RESPONSE_BYTES + 1)
            if not isinstance(raw_response, bytes):
                raise ProviderError("OpenAI returned a non-bytes HTTP response", retryable=True)
            if len(raw_response) > _MAX_RESPONSE_BYTES:
                raise ProviderError("OpenAI response exceeded the safe size limit")
            return raw_response
        except HTTPError as error:
            raise _http_error(error.code) from None
        except TimeoutError:
            raise ProviderTimeout("OpenAI request timed out") from None
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise ProviderTimeout("OpenAI request timed out") from None
            raise ProviderError("OpenAI request failed", retryable=True) from None
        except HTTPException:
            raise ProviderError(
                "OpenAI returned a truncated HTTP response", retryable=True
            ) from None
        except OSError:
            raise ProviderError("OpenAI request failed", retryable=True) from None
        finally:
            if response is not None:
                close = getattr(response, "close", None)
                if callable(close):
                    close()

    def _decode_response(self, raw_response: bytes) -> Mapping[str, Any]:
        try:
            payload = json.loads(
                raw_response.decode("utf-8"),
                parse_constant=_reject_json_constant,
                object_pairs_hook=_reject_duplicate_pairs,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
            raise ProviderError("OpenAI returned malformed JSON", retryable=True) from None
        if not isinstance(payload, Mapping):
            raise ProviderError("OpenAI returned an invalid response object", retryable=True)

        status = payload.get("status")
        if status is not None and not isinstance(status, str):
            raise ProviderError("OpenAI response had an invalid status", retryable=True)
        if status == "incomplete":
            reason = _incomplete_reason(payload)
            if reason in {"content_filter", "safety"}:
                raise ProviderRefusal("OpenAI did not complete the request for safety reasons")
            raise ProviderError(
                f"OpenAI response was incomplete ({reason or 'unknown reason'})",
                retryable=True,
            )
        if status in {"failed", "cancelled"}:
            error_code = _response_error_code(payload)
            raise ProviderError(
                f"OpenAI response failed ({error_code or status})",
                retryable=_is_retryable_response_error(error_code),
            )
        if status in {"queued", "in_progress"}:
            raise ProviderError("OpenAI response did not finish synchronously", retryable=True)
        if status is not None and status != "completed":
            raise ProviderError("OpenAI response had an unknown status", retryable=True)

        output = payload.get("output")
        if not isinstance(output, list):
            raise ProviderError("OpenAI response did not contain output", retryable=True)

        output_text_parts: list[str] = []
        for output_item in output:
            if not isinstance(output_item, Mapping) or output_item.get("type") != "message":
                continue
            content = output_item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, Mapping):
                    continue
                content_type = content_item.get("type")
                if content_type == "refusal":
                    raise ProviderRefusal("OpenAI model refused the structured request")
                if content_type == "output_text" and isinstance(content_item.get("text"), str):
                    output_text_parts.append(content_item["text"])

        if not output_text_parts:
            raise ProviderError("OpenAI response did not contain output_text", retryable=True)

        try:
            structured_output = json.loads(
                "".join(output_text_parts),
                parse_constant=_reject_json_constant,
                object_pairs_hook=_reject_duplicate_pairs,
            )
        except (json.JSONDecodeError, RecursionError, ValueError):
            raise ProviderError("OpenAI output_text was not valid JSON", retryable=True) from None
        if not isinstance(structured_output, Mapping):
            raise ProviderError("OpenAI structured output was not an object", retryable=True)
        return dict(structured_output)


def _response_status(response: Any) -> int | None:
    status = getattr(response, "status", None)
    if isinstance(status, int):
        return status
    getcode = getattr(response, "getcode", None)
    if callable(getcode):
        code = getcode()
        if isinstance(code, int):
            return code
    return None


class _NoRedirectHandler(HTTPRedirectHandler):
    """Keep bearer credentials on the single allowlisted OpenAI endpoint."""

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


def _validate_api_url(api_url: str) -> None:
    parsed = urlparse(api_url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "api.openai.com"
        or parsed.path != "/v1/responses"
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ProviderConfigurationError(
            "OpenAI Responses API URL must be https://api.openai.com/v1/responses"
        )


def _http_error(status_code: int) -> ProviderError:
    if status_code in {401, 403}:
        return ProviderConfigurationError(
            "OpenAI authentication or authorization failed",
            status_code=status_code,
        )
    retryable = status_code in _RETRYABLE_HTTP_STATUSES or status_code >= 500
    return ProviderError(
        f"OpenAI request failed with HTTP {status_code}",
        retryable=retryable,
        status_code=status_code,
    )


def _incomplete_reason(payload: Mapping[str, Any]) -> str | None:
    details = payload.get("incomplete_details")
    if not isinstance(details, Mapping):
        return None
    reason = details.get("reason")
    return reason if isinstance(reason, str) else None


def _response_error_code(payload: Mapping[str, Any]) -> str | None:
    error = payload.get("error")
    if not isinstance(error, Mapping):
        return None
    code = error.get("code")
    return code if isinstance(code, str) else None


def _is_retryable_response_error(error_code: str | None) -> bool:
    if error_code is None:
        return True
    return error_code in {
        "server_error",
        "rate_limit_exceeded",
        "vector_store_timeout",
    }


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Unsupported JSON constant: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    decoded: dict[str, Any] = {}
    for key, value in pairs:
        if key in decoded:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        decoded[key] = value
    return decoded
