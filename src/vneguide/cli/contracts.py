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


SessionFactory = Callable[[], ConversationSession]
