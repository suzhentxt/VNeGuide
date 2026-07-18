"""Deep-agent layer: grounded fact-retrieval tools, skills, and session adapter."""

from __future__ import annotations

from .tools import ToolContext, build_tools

__all__ = ["ToolContext", "build_tools"]
