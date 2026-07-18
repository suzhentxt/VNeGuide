"""LiteLLM/OpenAI-compatible Chat Completions adapter."""

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

_SCHEMA_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_RETRYABLE_HTTP_STATUSES = {408, 409, 425, 429}
_MAX_RESPONSE_BYTES = 2_000_000
_CHAT_COMPLETIONS_PATH = "/v1/chat/completions"
_THINKING_CLOSE_PATTERN = re.compile(r"</think\s*>", flags=re.IGNORECASE)


class LiteLLMChatCompletionsProvider:
    """Send strict structured requests to a configured LiteLLM gateway."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        allow_insecure_http: bool = False,
        disable_thinking: bool = True,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ProviderConfigurationError("LiteLLM model is required")
        if api_key is not None:
            _validate_api_key(api_key)
        if type(allow_insecure_http) is not bool or type(disable_thinking) is not bool:
            raise ProviderConfigurationError("LiteLLM boolean configuration is invalid")

        self._api_url = _chat_completions_url(
            base_url,
            allow_insecure_http=allow_insecure_http,
        )
        self._model = model.strip()
        self._api_key = api_key
        self._disable_thinking = disable_thinking
        self._opener = opener

    def generate_structured(self, request: StructuredRequest) -> Mapping[str, Any]:
        """Return the JSON object contained in the first completed choice."""

        if not _SCHEMA_NAME_PATTERN.fullmatch(request.schema_name):
            raise ProviderConfigurationError(
                "schema_name must contain 1-64 letters, digits, underscores, or dashes"
            )

        payload: dict[str, Any] = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.schema_name,
                    "schema": dict(request.json_schema),
                    "strict": True,
                },
            },
            "stream": False,
        }
        if self._disable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}

        try:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError):
            raise ProviderConfigurationError(
                "LiteLLM request payload could not be encoded"
            ) from None

        headers = {"Content-Type": "application/json"}
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"
        http_request = Request(
            self._api_url,
            data=body,
            headers=headers,
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
                raise ProviderError("LiteLLM returned a non-bytes HTTP response", retryable=True)
            if len(raw_response) > _MAX_RESPONSE_BYTES:
                raise ProviderError("LiteLLM response exceeded the safe size limit")
            return raw_response
        except HTTPError as error:
            raise _http_error(error.code) from None
        except TimeoutError:
            raise ProviderTimeout("LiteLLM request timed out") from None
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise ProviderTimeout("LiteLLM request timed out") from None
            raise ProviderError("LiteLLM request failed", retryable=True) from None
        except HTTPException:
            raise ProviderError(
                "LiteLLM returned a truncated HTTP response",
                retryable=True,
            ) from None
        except OSError:
            raise ProviderError("LiteLLM request failed", retryable=True) from None
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
            raise ProviderError("LiteLLM returned malformed JSON", retryable=True) from None
        if not isinstance(payload, Mapping):
            raise ProviderError("LiteLLM returned an invalid response object", retryable=True)

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderError("LiteLLM response did not contain choices", retryable=True)
        choice = choices[0]
        if not isinstance(choice, Mapping):
            raise ProviderError("LiteLLM returned an invalid choice", retryable=True)

        finish_reason = choice.get("finish_reason")
        if finish_reason in {"content_filter", "safety"}:
            raise ProviderRefusal("LiteLLM did not complete the request for safety reasons")
        if finish_reason == "length":
            raise ProviderError("LiteLLM output reached its token limit", retryable=True)
        if finish_reason != "stop":
            raise ProviderError("LiteLLM returned an unsupported finish reason", retryable=True)

        message = choice.get("message")
        if not isinstance(message, Mapping):
            raise ProviderError("LiteLLM response did not contain a message", retryable=True)
        refusal = message.get("refusal")
        if isinstance(refusal, str) and refusal:
            raise ProviderRefusal("LiteLLM model refused the structured request")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("LiteLLM response did not contain content", retryable=True)

        structured_output = _decode_structured_content(content)
        if not isinstance(structured_output, Mapping):
            raise ProviderError("LiteLLM structured output was not an object", retryable=True)
        return dict(structured_output)


class _NoRedirectHandler(HTTPRedirectHandler):
    """Never forward a configured bearer credential across redirects."""

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


def _decode_structured_content(content: str) -> object:
    """Decode strict JSON, retrying only after a leading Qwen thinking block.

    The clean response is always parsed first.  Recovery never searches for an
    arbitrary JSON fragment: it only accepts content following a closing
    ``</think>`` marker when that remainder starts with a JSON object.  The
    second parse stays strict, including duplicate-key and non-finite checks.
    """

    try:
        return _strict_json_loads(content)
    except (json.JSONDecodeError, RecursionError, ValueError):
        recovered = _content_after_thinking_prefix(content)
        if recovered is None:
            raise ProviderError("LiteLLM content was not valid JSON", retryable=True) from None
    try:
        return _strict_json_loads(recovered)
    except (json.JSONDecodeError, RecursionError, ValueError):
        raise ProviderError("LiteLLM content was not valid JSON", retryable=True) from None


def _strict_json_loads(content: str) -> object:
    return json.loads(
        content,
        parse_constant=_reject_json_constant,
        object_pairs_hook=_reject_duplicate_pairs,
    )


def _content_after_thinking_prefix(content: str) -> str | None:
    stripped = content.strip()
    if stripped.startswith("{"):
        return None
    matches = tuple(_THINKING_CLOSE_PATTERN.finditer(stripped))
    for match in reversed(matches):
        candidate = stripped[match.end() :].strip()
        if candidate.startswith("{"):
            return candidate
    return None


def _open_without_redirects(request: Request, *, timeout: float) -> Any:
    return build_opener(_NoRedirectHandler()).open(request, timeout=timeout)


def _chat_completions_url(base_url: str, *, allow_insecure_http: bool) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise ProviderConfigurationError("LiteLLM base URL is required")
    if any(ord(character) < 32 or ord(character) == 127 for character in base_url):
        raise ProviderConfigurationError("LiteLLM base URL is invalid")
    try:
        parsed = urlparse(base_url.strip())
        _ = parsed.port
    except ValueError:
        raise ProviderConfigurationError("LiteLLM base URL is invalid") from None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ProviderConfigurationError("LiteLLM base URL must use HTTP or HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ProviderConfigurationError("LiteLLM base URL must not contain credentials")
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise ProviderConfigurationError(
            "LiteLLM base URL must contain only scheme, host, and port"
        )
    if parsed.scheme == "http" and not allow_insecure_http:
        raise ProviderConfigurationError(
            "LiteLLM HTTP requires VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=1"
        )
    return f"{parsed.scheme}://{parsed.netloc}{_CHAT_COMPLETIONS_PATH}"


def _validate_api_key(api_key: str) -> None:
    if (
        not isinstance(api_key, str)
        or not api_key
        or not api_key.isascii()
        or any(not 33 <= ord(character) <= 126 for character in api_key)
    ):
        raise ProviderConfigurationError("LiteLLM API key format is invalid")


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


def _http_error(status_code: int) -> ProviderError:
    if status_code in {401, 403}:
        return ProviderConfigurationError(
            "LiteLLM authentication or authorization failed",
            status_code=status_code,
        )
    retryable = status_code in _RETRYABLE_HTTP_STATUSES or status_code >= 500
    return ProviderError(
        f"LiteLLM request failed with HTTP {status_code}",
        retryable=retryable,
        status_code=status_code,
    )


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Unsupported JSON constant: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    decoded: dict[str, Any] = {}
    for key, value in pairs:
        if key in decoded:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        decoded[key] = value
    return decoded


__all__ = ["LiteLLMChatCompletionsProvider"]
