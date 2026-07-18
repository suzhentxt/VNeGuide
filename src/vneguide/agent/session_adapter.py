"""Adapter that wraps the deep agent as a ``ConversationSession`` subclass.

``DeepAgentSession`` inherits all state management (draft, suggestions,
revision, extraction) from :class:`ConversationSession` and overrides
:meth:`send` to re-compose informational replies via the deep agent — where
the LLM proactively calls grounded tools and writes a natural-language answer.

For the MVP, ``send()`` calls ``super().send()`` to preserve all state
transitions, then — when the turn is an informational Q&A
(``NextAction.PRESENT_GUIDANCE`` or ``ASK_CLARIFICATION``) — re-composes the
reply via the deep agent. This demonstrates the agent's proactive tool calling
without breaking the form-filling lifecycle.
"""

from __future__ import annotations

import json
from typing import Any, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph.state import CompiledStateGraph

from vneguide.domain import ConversationState, NextAction, TurnResult
from vneguide.rules import ProcedureQAResponder, QuestionSelector, RuleEngine

from ..core.session import ConversationSession, Extractor, Responder
from ..data import ProcedureRepository
from .agent import build_agent
from .tools import ToolContext, build_tools

_PRESENTATION_ACTIONS = frozenset({NextAction.PRESENT_GUIDANCE, NextAction.ASK_CLARIFICATION})


def _message_text(msg: AIMessage) -> str:
    """Extract plain text from an AIMessage whose content may be a list."""

    content = msg.content
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "".join(parts)


class DeepAgentSession(ConversationSession):
    """``ConversationSession`` that re-composes informational replies via the deep agent."""

    def __init__(
        self,
        model: BaseChatModel,
        extractor: Extractor,
        repository: ProcedureRepository,
        *,
        responder: Responder | None = None,
        compactor: Any | None = None,
    ) -> None:
        super().__init__(
            extractor,
            repository,
            responder=responder,
            compactor=compactor,
        )
        self._model = model
        self._ctx = ToolContext(
            repository=repository,
            qa_responder=ProcedureQAResponder(repository),
            rule_engine=RuleEngine(repository),
            question_selector=QuestionSelector(repository),
        )
        self._tools = build_tools(self._ctx)
        self._thread_id = str(id(self))
        self._agent: CompiledStateGraph[Any, Any, Any] = build_agent(
            model, self._tools, thread_id=self._thread_id
        )

    def send(self, message: str) -> TurnResult:
        result = super().send(message)
        if result.next_action in _PRESENTATION_ACTIONS:
            return self._recompose_with_agent(message, result)
        return result

    def _recompose_with_agent(self, message: str, result: TurnResult) -> TurnResult:
        """Re-compose an informational reply using the deep agent.

        The agent calls grounded tools and writes a natural-language answer.
        If the agent fails or returns empty, fall back to the delegate's reply.
        """

        config: dict[str, Any] = {
            "configurable": {"thread_id": self._thread_id},
            "recursion_limit": 20,
        }
        procedure_code = (
            result.state.draft.procedure_code
            or result.state.pending_procedure_code
            or result.state.recent_information_procedure_code
        )
        context_hint = ""
        if procedure_code is not None:
            context_hint = f"\n\n[Ngữ cảnh: thủ tục {procedure_code.value}]"
        try:
            agent_result = cast(
                dict[str, Any],
                self._agent.invoke(
                    cast(Any, {"messages": [HumanMessage(content=message + context_hint)]}),
                    config=cast(Any, config),
                ),
            )
        except Exception:
            return result

        messages = agent_result.get("messages", [])
        if not messages:
            return result
        last = messages[-1]
        if not isinstance(last, AIMessage):
            return result
        reply_text = _message_text(last).strip()
        if not reply_text:
            return result

        source_ids = self._collect_source_ids(messages)
        new_state = ConversationState(
            draft=result.state.draft,
            pending_procedure_code=result.state.pending_procedure_code,
            messages=result.state.messages,
            turn_number=result.state.turn_number,
            clarification_attempts=result.state.clarification_attempts,
            suggestions=result.state.suggestions,
            asked_question_ids=result.state.asked_question_ids,
            recent_information_procedure_code=result.state.recent_information_procedure_code,
            recent_information_topics=result.state.recent_information_topics,
            memory_summary=result.state.memory_summary,
        )
        return TurnResult(
            reply=reply_text,
            state=new_state,
            next_action=result.next_action,
            source_ids=source_ids or result.source_ids,
            missing_fields=result.missing_fields,
            validation=result.validation,
            extracted_fields=result.extracted_fields,
        )

    def _collect_source_ids(self, messages: list[Any]) -> tuple[str, ...]:
        """Extract ``source_ids`` from tool-call results in the message history."""

        ids: list[str] = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                content = msg.content
                if isinstance(content, str):
                    try:
                        parsed = json.loads(content)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if isinstance(parsed, dict):
                        raw_ids = parsed.get("source_ids", [])
                        if isinstance(raw_ids, list):
                            ids.extend(str(sid) for sid in raw_ids)
        seen: dict[str, None] = {}
        for sid in ids:
            if sid not in seen:
                seen[sid] = None
        return tuple(seen)


__all__ = ["DeepAgentSession"]
