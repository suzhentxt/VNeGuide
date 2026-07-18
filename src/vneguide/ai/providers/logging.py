"""Dev-only wrapper that records every structured LLM call to a JSONL file.

Each line is a JSON object with the timestamp, schema name, model, prompts,
parsed response (or error), and latency. The log stays on the local filesystem
under ``logs/`` (gitignored) and never leaves the machine — it is a debugging
aid, not a production telemetry sink. Prompts contain raw citizen input, so
the file must never be committed or shipped.
"""

from __future__ import annotations

import json
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
            _write_record(
                self._log_path,
                schema_name=request.schema_name,
                model=self._model,
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                response=response if status == "success" else None,
                status=status,
                error=error,
                latency_ms=int((_monotonic_seconds() - started) * 1000),
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
