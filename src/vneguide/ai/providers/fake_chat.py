"""Scripted fake chat model for tests.

Mirrors the deque-based :class:`MockLLMProvider` pattern: tests enqueue
``AIMessage`` objects (with optional ``tool_calls``) and the model pops them in
order. Supports ``bind_tools`` and ``with_structured_output`` so it can stand in
for :class:`langchain_openai.ChatOpenAI` in the deep-agent layer.

Each invocation records the prompt messages in ``self.calls`` for assertions.

``bind_tools`` returns a view that shares the same response deque and call log
as the original, so responses are consumed across model-node re-invocations
inside a LangGraph agent loop (the agent may call ``bind_tools`` more than once).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class FakeChatModel(BaseChatModel):
    """Pops scripted ``AIMessage`` responses; records every call."""

    responses: deque[AIMessage] = deque()
    model_name: str = "fake-chat"
    _bound_tools: list[Any] = []
    _structured_schema: dict[str, Any] | None = None

    def __init__(
        self,
        responses: Sequence[AIMessage | str] | None = None,
        *,
        model_name: str = "fake-chat",
    ) -> None:
        super().__init__()
        shared: deque[AIMessage] = deque(
            msg if isinstance(msg, AIMessage) else AIMessage(content=msg)
            for msg in (responses or [])
        )
        object.__setattr__(self, "responses", shared)
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "calls", [])
        object.__setattr__(self, "_bound_tools", [])
        object.__setattr__(self, "_structured_schema", None)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        calls: list[Any] = getattr(self, "calls", None) or []
        calls.append(list(messages))
        object.__setattr__(self, "calls", calls)

        queue: deque[AIMessage] = getattr(self, "responses", deque())
        if not queue:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=""))])
        message = queue.popleft()
        object.__setattr__(self, "responses", queue)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> BaseChatModel:
        bound = self.model_copy()
        object.__setattr__(bound, "_bound_tools", list(tools))
        object.__setattr__(bound, "responses", getattr(self, "responses", deque()))
        object.__setattr__(bound, "calls", getattr(self, "calls", []))
        return bound

    def with_structured_output(
        self,
        schema: Any,
        **kwargs: Any,
    ) -> Any:
        bound = self.model_copy()
        schema_dict = schema if isinstance(schema, dict) else None
        object.__setattr__(bound, "_structured_schema", schema_dict)
        object.__setattr__(bound, "responses", getattr(self, "responses", deque()))
        object.__setattr__(bound, "calls", getattr(self, "calls", []))
        return bound

    @property
    def _llm_type(self) -> str:
        return "fake-chat"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model_name": "fake-chat"}

    @property
    def remaining(self) -> int:
        return len(getattr(self, "responses", deque()))

    def enqueue(self, message: AIMessage | str) -> None:
        queue: deque[AIMessage] = getattr(self, "responses", deque())
        queue.append(message if isinstance(message, AIMessage) else AIMessage(content=message))
        object.__setattr__(self, "responses", queue)


__all__ = ["FakeChatModel"]
