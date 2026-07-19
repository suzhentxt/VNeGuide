"""CLI-owned integration ports.

These protocols deliberately do not redefine any domain contract. A session
implementation keeps ``ConversationState`` internally and returns the shared
``TurnResult`` object from ``send``.
"""

from collections.abc import Callable
from typing import Any, Protocol


class ConversationSession(Protocol):
    """Stateful adapter around the public conversation orchestrator."""

    def send(self, message: str) -> Any:
        """Process one user message and return a domain ``TurnResult``."""


# A factory returns a fresh session. The default ``create_session`` accepts an
# optional ``mock_responses`` keyword (used by integration tests to script the
# mock provider); production callers invoke it with no arguments. ``Callable[...]``
# keeps the port open without forcing every factory to accept that keyword.
SessionFactory = Callable[..., ConversationSession]


__all__ = ["ConversationSession", "SessionFactory"]
