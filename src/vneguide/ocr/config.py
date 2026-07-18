"""Environment configuration for the isolated OpenAI OCR worker."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class OcrConfig:
    enabled: bool
    model_id: str
    api_key: str | None = field(repr=False)
    worker_token: str | None = field(repr=False)
    max_queued_jobs: int = 2
    job_timeout_seconds: int = 60
    result_ttl_seconds: int = 600


def load_ocr_config(
    environ: Mapping[str, str] | None = None,
    *,
    env_file: str | Path | None = None,
) -> OcrConfig:
    source: dict[str, str] = {}
    if env_file is not None:
        source.update(_read_env_file(Path(env_file)))
    source.update(os.environ if environ is None else environ)
    return OcrConfig(
        enabled=_boolean(source, "VNEGUIDE_OCR_ENABLED", False),
        model_id=source.get("VNEGUIDE_OCR_MODEL", "gpt-5.5").strip() or "gpt-5.5",
        api_key=(
            source.get("VNEGUIDE_OCR_OPENAI_API_KEY", "").strip()
            or source.get("VNEGUIDE_API_KEY", "").strip()
            or None
        ),
        worker_token=source.get("VNEGUIDE_OCR_WORKER_TOKEN", "").strip() or None,
        max_queued_jobs=_positive_int(source, "VNEGUIDE_OCR_MAX_QUEUED_JOBS", 2),
        job_timeout_seconds=_positive_int(source, "VNEGUIDE_OCR_JOB_TIMEOUT_SECONDS", 60),
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


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, raw_value = line.split("=", 1)
        name = name.strip()
        if not name:
            continue
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[name] = value
    return values


__all__ = ["OcrConfig", "load_ocr_config"]
