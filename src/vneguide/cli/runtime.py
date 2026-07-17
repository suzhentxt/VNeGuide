"""Resolve the conversation session supplied by the core integration."""

from __future__ import annotations

import importlib
import os
from typing import cast

from vneguide.cli.contracts import SessionFactory

DEFAULT_SESSION_FACTORY = "vneguide.core:create_session"
SESSION_FACTORY_ENV = "VNEGUIDE_SESSION_FACTORY"


class CliConfigurationError(RuntimeError):
    """Raised when the CLI cannot load its conversation session factory."""


def load_session_factory(path: str | None = None) -> SessionFactory:
    """Load a ``module:callable`` session factory.

    The default points to the public integration hook owned by ``core``. It is
    imported lazily so renderer and command tests do not require a model API key
    or a completed core implementation.
    """

    target = path or os.getenv(SESSION_FACTORY_ENV) or DEFAULT_SESSION_FACTORY
    module_name, separator, attribute_name = target.partition(":")
    if not separator or not module_name or not attribute_name:
        raise CliConfigurationError(f"{SESSION_FACTORY_ENV} phải có dạng 'package.module:factory'.")

    try:
        module = importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError) as exc:
        raise CliConfigurationError(f"Không thể import module tích hợp '{module_name}'.") from exc

    try:
        factory = getattr(module, attribute_name)
    except AttributeError as exc:
        raise CliConfigurationError(
            f"Module '{module_name}' chưa cung cấp factory '{attribute_name}'."
        ) from exc

    if not callable(factory):
        raise CliConfigurationError(f"'{target}' không phải là một factory callable.")
    return cast(SessionFactory, factory)
