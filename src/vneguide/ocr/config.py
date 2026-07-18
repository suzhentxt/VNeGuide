"""Environment configuration for the local OCR worker."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class OcrConfig:
    enabled: bool
    model_id: str
    worker_token: str | None = field(repr=False)
    max_queued_jobs: int = 2
    job_timeout_seconds: int = 300
    result_ttl_seconds: int = 600


def load_ocr_config(environ: Mapping[str, str] | None = None) -> OcrConfig:
    source = os.environ if environ is None else environ
    return OcrConfig(
        enabled=_boolean(source, "VNEGUIDE_OCR_ENABLED", False),
        model_id=source.get("VNEGUIDE_MODEL", "Qwen/Qwen3.5-9B").strip() or "Qwen/Qwen3.5-9B",
        worker_token=source.get("VNEGUIDE_OCR_WORKER_TOKEN", "").strip() or None,
        max_queued_jobs=_positive_int(source, "VNEGUIDE_OCR_MAX_QUEUED_JOBS", 2),
        job_timeout_seconds=_positive_int(source, "VNEGUIDE_OCR_JOB_TIMEOUT_SECONDS", 300),
        result_ttl_seconds=_positive_int(source, "VNEGUIDE_OCR_RESULT_TTL_SECONDS", 600),
    )


def _boolean(source: Mapping[str, str], name: str, default: bool) -> bool:
    raw = source.get(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def _positive_int(source: Mapping[str, str], name: str, default: int) -> int:
    raw = source.get(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


__all__ = ["OcrConfig", "load_ocr_config"]
