from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest

from vneguide.api.session_store import ChatSession, InMemorySessionStore, SessionExpiredError
from vneguide.domain import ConversationState


@dataclass
class Clock:
    value: float = 0.0

    def __call__(self) -> float:
        return self.value


class EmptySession:
    def __init__(self) -> None:
        self._state = ConversationState()
        self.closed = False

    @property
    def state(self) -> ConversationState:
        return self._state

    def close(self) -> None:
        self.closed = True


def test_session_store_expires_and_closes_sessions() -> None:
    clock = Clock()
    session = EmptySession()
    store = InMemorySessionStore(
        lambda: cast(ChatSession, session),
        ttl_seconds=10,
        clock=clock,
    )
    session_id, _entry = store.create()

    clock.value = 11

    with pytest.raises(SessionExpiredError):
        store.get(session_id)
    assert session.closed is True
