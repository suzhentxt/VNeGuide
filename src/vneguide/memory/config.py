"""Opt-in Mem0 composition with local Qdrant persistence."""

from __future__ import annotations

import os
import threading
import warnings
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import cast

from .service import LongTermMemory, Mem0Client

_LOCK = threading.Lock()
_CACHE: dict[MemoryConfig, LongTermMemory | None] = {}


class MemoryConfigurationError(RuntimeError):
    """The requested long-term memory configuration is unsafe or incomplete."""


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    provider: str = "disabled"
    allow_external_embeddings: bool = False
    api_key: str | None = field(default=None, repr=False)
    llm_model: str = "unused-with-infer-false"
    embedding_model: str = "text-embedding-3-small"
    embedding_dims: int = 1536
    store_dir: Path = Path(".vneguide-memory")


def load_memory_config(environ: Mapping[str, str] | None = None) -> MemoryConfig:
    source = os.environ if environ is None else environ
    provider = source.get("VNEGUIDE_MEMORY_PROVIDER", "disabled").strip().lower() or "disabled"
    if provider not in {"disabled", "mem0"}:
        raise MemoryConfigurationError("VNEGUIDE_MEMORY_PROVIDER must be disabled or mem0")
    allow_external = _boolean(source, "VNEGUIDE_MEM0_ALLOW_EXTERNAL", default=False)
    store_dir = Path(source.get("VNEGUIDE_MEM0_STORE_DIR", ".vneguide-memory").strip())
    if not str(store_dir):
        raise MemoryConfigurationError("VNEGUIDE_MEM0_STORE_DIR must not be empty")
    return MemoryConfig(
        provider=provider,
        allow_external_embeddings=allow_external,
        api_key=source.get("VNEGUIDE_API_KEY", "").strip() or None,
        embedding_model=(
            source.get("VNEGUIDE_MEM0_EMBEDDING_MODEL", "text-embedding-3-small").strip()
            or "text-embedding-3-small"
        ),
        embedding_dims=_positive_int(source, "VNEGUIDE_MEM0_EMBEDDING_DIMS", 1536),
        store_dir=store_dir,
    )


def build_memory(config: MemoryConfig) -> LongTermMemory | None:
    """Build one shared Mem0 client; disabled remains a zero-dependency path."""

    with _LOCK:
        if config in _CACHE:
            return _CACHE[config]
        memory = _build_uncached(config)
        _CACHE[config] = memory
        return memory


def _build_uncached(config: MemoryConfig) -> LongTermMemory | None:
    if config.provider == "disabled":
        return None
    if not config.allow_external_embeddings:
        raise MemoryConfigurationError(
            "Mem0 uses an external embedding provider; set VNEGUIDE_MEM0_ALLOW_EXTERNAL=1 "
            "only after obtaining consent for the normalized preferences sent to it"
        )
    if config.api_key is None:
        raise MemoryConfigurationError("Mem0 requires VNEGUIDE_API_KEY when enabled")

    # Mem0 telemetry is opt-out upstream. VNeGuide disables it before importing
    # the SDK so memory use does not emit product analytics.
    os.environ["MEM0_TELEMETRY"] = "False"
    try:
        memory_module = import_module("mem0")
    except ImportError:
        warnings.warn(
            "Mem0 is enabled but mem0ai is not installed; long-term memory is disabled",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    memory_class = memory_module.Memory

    # Keep opt-out effective even if another dependency imported Mem0 first.
    for module_name in ("mem0.memory.telemetry", "mem0.memory.main"):
        telemetry_module = import_module(module_name)
        telemetry_module.__dict__["MEM0_TELEMETRY"] = False

    try:
        store_dir = config.store_dir.resolve()
        store_dir.mkdir(parents=True, exist_ok=True)
        client = memory_class.from_config(
            {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "collection_name": "vneguide_preferences",
                        "embedding_model_dims": config.embedding_dims,
                        "path": str(store_dir / "qdrant"),
                        "on_disk": True,
                    },
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "api_key": config.api_key,
                        "model": config.embedding_model,
                    },
                },
                "llm": {
                    "provider": "openai",
                    "config": {"api_key": config.api_key, "model": config.llm_model},
                },
                "history_db_path": str(store_dir / "history.db"),
            }
        )
    except Exception:
        warnings.warn(
            "Mem0 could not initialize; long-term memory is disabled for this process",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    return LongTermMemory(cast(Mem0Client, client))


def _boolean(source: Mapping[str, str], name: str, *, default: bool) -> bool:
    raw = source.get(name)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise MemoryConfigurationError(f"{name} must be a boolean value")


def _positive_int(source: Mapping[str, str], name: str, default: int) -> int:
    raw = source.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise MemoryConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise MemoryConfigurationError(f"{name} must be positive")
    return value


__all__ = ["MemoryConfig", "MemoryConfigurationError", "build_memory", "load_memory_config"]
