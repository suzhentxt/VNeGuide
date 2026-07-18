"""Build the VNeGuide deep agent from the ``deepagents`` harness.

The agent uses :func:`create_deep_agent` with:
- Our 15 grounded fact-retrieval tools (Phase 1).
- A safe harness profile that excludes ``execute``, filesystem tools, and
  ``task`` (subagents) — the agent cannot run shell, touch the real disk, or
  spawn subagents. The default ``StateBackend`` is in-memory only.
- Skills loaded from ``./skills/`` (one per procedure).
- No subagents, no long-term memory store (kept simple for the MVP).

The agent IS proactive: it decides which tool to call based on the citizen's
message. But every tool returns reviewed data with ``source_ids``; the LLM
cannot author facts. This is the safe relaxation of AGENTS.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from .prompts import BASE_SYSTEM_PROMPT

_EXCLUDED_BUILTIN_TOOLS = frozenset(
    ["execute", "ls", "read_file", "write_file", "edit_file", "glob", "grep", "task"]
)

_PROFILE_REGISTERED = False


def _ensure_safe_profile_registered(model: BaseChatModel) -> None:
    """Register a harness profile that excludes dangerous built-in tools.

    ``deepagents`` matches profiles by ``provider:identifier``. We register
    under every key we might see (the real GLM model and the fake test model)
    so the exclusion applies in both prod and tests.
    """

    global _PROFILE_REGISTERED
    if _PROFILE_REGISTERED:
        return

    from deepagents import HarnessProfile, register_harness_profile

    profile = HarnessProfile(excluded_tools=_EXCLUDED_BUILTIN_TOOLS)
    for key in ("openai:zai-org/GLM-5.2", "fakechatmodel:fake-chat"):
        try:
            register_harness_profile(key, profile)
        except Exception:
            pass
    _PROFILE_REGISTERED = True


def build_agent(
    model: BaseChatModel,
    tools: list[BaseTool],
    *,
    skills_dir: Path | None = None,
    thread_id: str = "default",
) -> CompiledStateGraph[Any, Any, Any]:
    """Build a deep agent bound to ``model`` and ``tools``.

    Args:
        model: LangChain chat model (GLM or fake).
        tools: Grounded fact-retrieval tools from :func:`build_tools`.
        skills_dir: Directory containing skill subdirectories. If ``None``,
            skills are loaded from ``./skills/`` relative to this package.
        thread_id: Checkpointer thread ID for this session.
    """

    _ensure_safe_profile_registered(model)

    from deepagents import create_deep_agent

    if skills_dir is None:
        skills_dir = Path(__file__).parent / "skills"

    checkpointer = MemorySaver()

    return create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=BASE_SYSTEM_PROMPT,
        skills=[str(skills_dir)],
        checkpointer=checkpointer,
    )


__all__ = ["build_agent"]
