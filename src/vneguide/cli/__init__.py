"""Terminal interface for VNeGuide.

The CLI depends on a small session port so it can be integrated with the public
conversation engine without importing or duplicating domain models.
"""

from vneguide.cli.app import TerminalApp, main
from vneguide.cli.contracts import ConversationSession, SessionFactory

__all__ = ["ConversationSession", "SessionFactory", "TerminalApp", "main"]
