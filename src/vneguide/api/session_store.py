"""Bounded in-memory sessions for the single-process demo API."""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Protocol

from vneguide.domain import ConversationState, JSONValue, ProcedureCode, TurnResult

from .schemas import SessionContext


class ChatSession(Protocol):
    @property
    def state(self) -> ConversationState: ...

    def initialize_procedure(self, procedure_code: ProcedureCode | str) -> None: ...

    def send(self, message: str) -> TurnResult: ...

    def accept_suggestion(self, suggestion_id: str, *, expected_revision: int) -> TurnResult: ...

    def reject_suggestion(self, suggestion_id: str, *, expected_revision: int) -> TurnResult: ...

    def edit_suggestion(
        self,
        suggestion_id: str,
        value: JSONValue,
        *,
        expected_revision: int,
    ) -> TurnResult: ...

    def edit_field(
        self,
        field_id: str,
        value: JSONValue,
        *,
        expected_revision: int,
        user_message: str | None = None,
    ) -> TurnResult: ...

    def close(self) -> None: ...


class SessionStoreError(RuntimeError):
    """Base class for safe session lookup failures."""


class SessionNotFoundError(SessionStoreError):
    pass


class SessionExpiredError(SessionStoreError):
    pass


class SessionCapacityError(SessionStoreError):
    pass


@dataclass(slots=True)
class SessionEntry:
    session: ChatSession
    context: SessionContext | None
    expires_at: float
    last_result: TurnResult | None = None
    turn_results: dict[str, TurnResult] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)


class InMemorySessionStore:
    def __init__(
        self,
        factory: Callable[[], ChatSession],
        *,
        ttl_seconds: int = 1_800,
        max_active: int = 100,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_active <= 0:
            raise ValueError("max_active must be positive")
        self._factory = factory
        self._ttl_seconds = ttl_seconds
        self._max_active = max_active
        self._clock = clock
        self._entries: dict[str, SessionEntry] = {}
        self._lock = threading.RLock()

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def create(self, context: SessionContext | None = None) -> tuple[str, SessionEntry]:
        self._remove_expired()
        with self._lock:
            if len(self._entries) >= self._max_active:
                raise SessionCapacityError("session capacity reached")
            session_id = secrets.token_urlsafe(32)
            entry = SessionEntry(
                session=self._factory(),
                context=context,
                expires_at=self._clock() + self._ttl_seconds,
            )
            self._entries[session_id] = entry
            return session_id, entry

    def get(self, session_id: str) -> SessionEntry:
        """Return a refreshed entry for snapshot-only callers.

        Mutating callers must use :meth:`acquire` so reset and TTL cleanup
        cannot close the session while an operation is in progress.
        """

        with self.acquire(session_id) as entry:
            return entry

    @contextmanager
    def acquire(self, session_id: str) -> Iterator[SessionEntry]:
        """Lock one live entry atomically against delete and expiry."""

        with self._lock:
            entry = self._entries.get(session_id)
        if entry is None:
            raise SessionNotFoundError("unknown session")

        entry.lock.acquire()
        try:
            with self._lock:
                if self._entries.get(session_id) is not entry:
                    raise SessionNotFoundError("unknown session")
                expired = entry.expires_at <= self._clock()
                if expired:
                    self._entries.pop(session_id, None)
                else:
                    entry.expires_at = self._clock() + self._ttl_seconds
            if expired:
                entry.session.close()
                raise SessionExpiredError("session expired")
            yield entry
        finally:
            entry.lock.release()

    def delete(self, session_id: str) -> bool:
        with self._lock:
            entry = self._entries.get(session_id)
        if entry is None:
            return False
        with entry.lock:
            with self._lock:
                if self._entries.get(session_id) is not entry:
                    return False
                self._entries.pop(session_id, None)
            entry.session.close()
        return True

    def expires_in(self, entry: SessionEntry) -> int:
        return max(0, int(entry.expires_at - self._clock()))

    def _remove_expired(self) -> None:
        with self._lock:
            now = self._clock()
            expired_entries = [
                (session_id, entry)
                for session_id, entry in self._entries.items()
                if entry.expires_at <= now
            ]
        for session_id, entry in expired_entries:
            with entry.lock:
                with self._lock:
                    if (
                        self._entries.get(session_id) is not entry
                        or entry.expires_at > self._clock()
                    ):
                        continue
                    self._entries.pop(session_id, None)
                entry.session.close()
