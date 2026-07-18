"""Dev-only wrapper that records every structured LLM call.

Each call is appended as a JSON object to a JSONL file under ``logs/``
(gitignored) and a readable summary is printed to stderr so the backend
console shows each call in real time without tailing the file. Python writes
to the Windows console via the Unicode API, so Vietnamese renders correctly
whereas tailing the JSONL file from PowerShell can mangle it.

The log never leaves the machine — it is a debugging aid, not a production
telemetry sink. Prompts contain raw citizen input, so the file must never be
committed or shipped.
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .base import LLMProvider, ProviderError, StructuredRequest


class LoggingProvider:
    """Wrap an LLM provider and append one JSONL record per call."""

    def __init__(
        self,
        inner: LLMProvider,
        *,
        log_path: str | Path,
        model: str | None = None,
    ) -> None:
        self._inner = inner
        self._log_path = Path(log_path)
        self._model = model

    def generate_structured(self, request: StructuredRequest) -> object:
        started = _monotonic_seconds()
        status = "error"
        response: Any = None
        error: str | None = None
        try:
            response = self._inner.generate_structured(request)
            status = "success"
            return response
        except ProviderError as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            latency_ms = int((_monotonic_seconds() - started) * 1000)
            _write_record(
                self._log_path,
                schema_name=request.schema_name,
                model=self._model,
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                response=response if status == "success" else None,
                status=status,
                error=error,
                latency_ms=latency_ms,
            )
            _emit_console(
                schema_name=request.schema_name,
                model=self._model,
                user_prompt=request.user_prompt,
                response=response if status == "success" else None,
                status=status,
                error=error,
                latency_ms=latency_ms,
            )


def _write_record(
    log_path: Path,
    *,
    schema_name: str,
    model: str | None,
    system_prompt: str,
    user_prompt: str,
    response: object,
    status: str,
    error: str | None,
    latency_ms: int,
) -> None:
    record: dict[str, Any] = {
        "schema_name": schema_name,
        "model": model,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "response": _jsonable(response),
        "status": status,
        "latency_ms": latency_ms,
    }
    if error is not None:
        record["error"] = error
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _emit_console(
    *,
    schema_name: str,
    model: str | None,
    user_prompt: str,
    response: object,
    status: str,
    error: str | None,
    latency_ms: int,
) -> None:
    model_label = model or "?"
    prompt_preview = _truncate(user_prompt, 800)
    if status == "success":
        response_json = json.dumps(_jsonable(response), ensure_ascii=False)
        response_preview = _truncate(response_json, 2000)
        text = (
            f"\n[LLM:{schema_name}] {model_label} | {latency_ms}ms | success\n"
            f"  IN : {prompt_preview}\n"
            f"  OUT: {response_preview}\n"
        )
    else:
        text = (
            f"\n[LLM:{schema_name}] {model_label} | {latency_ms}ms | ERROR: {error or '?'}\n"
            f"  IN : {prompt_preview}\n"
        )
    _write_stderr(text)


def _write_stderr(text: str) -> None:
    # Write UTF-8 bytes directly to the underlying buffer so the Windows console
    # renders Vietnamese correctly via WriteConsoleW, bypassing the TextIOWrapper
    # encoding (which may be cp1252 and mangle or replace non-ASCII chars).
    buffer = getattr(sys.stderr, "buffer", None)
    if buffer is not None:
        try:
            buffer.write(text.encode("utf-8"))
            buffer.flush()
            return
        except (ValueError, OSError):
            pass
    print(text, file=sys.stderr, flush=True)


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def _jsonable(value: object) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def _monotonic_seconds() -> float:
    return time.monotonic()


__all__ = ["LoggingProvider"]
