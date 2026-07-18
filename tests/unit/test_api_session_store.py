from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, cast

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

    def is_closed(self) -> bool:
        return self.closed


class ObservedRLock:
    """Expose when another thread starts waiting for the entry lock."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._attempts_lock = threading.Lock()
        self._attempts = 0
        self.second_acquire_attempted = threading.Event()

    def acquire(self) -> bool:
        with self._attempts_lock:
            self._attempts += 1
            if self._attempts == 2:
                self.second_acquire_attempted.set()
        return self._lock.acquire()

    def release(self) -> None:
        self._lock.release()

    def __enter__(self) -> ObservedRLock:
        if not self.acquire():  # pragma: no cover - blocking acquire always succeeds
            raise RuntimeError("could not acquire observed lock")
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self.release()


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
    assert session.is_closed()


def test_delete_waits_for_an_acquired_operation_before_closing() -> None:
    session = EmptySession()
    store = InMemorySessionStore(lambda: cast(ChatSession, session))
    session_id, entry = store.create()
    observed_lock = ObservedRLock()
    entry.lock = cast(Any, observed_lock)
    acquired = threading.Event()
    release = threading.Event()
    operation_done = threading.Event()
    delete_done = threading.Event()
    deleted: list[bool] = []
    errors: list[BaseException] = []

    def hold_operation() -> None:
        try:
            with store.acquire(session_id):
                acquired.set()
                if not release.wait(timeout=2):
                    raise AssertionError("test did not release acquired operation")
                if session.closed:
                    raise AssertionError("session closed while operation was acquired")
        except BaseException as exc:  # pragma: no cover - surfaced by assertions below
            errors.append(exc)
        finally:
            operation_done.set()

    def delete_session() -> None:
        try:
            deleted.append(store.delete(session_id))
        except BaseException as exc:  # pragma: no cover - surfaced by assertions below
            errors.append(exc)
        finally:
            delete_done.set()

    operation_thread = threading.Thread(target=hold_operation)
    delete_thread = threading.Thread(target=delete_session)
    operation_thread.start()
    try:
        assert acquired.wait(timeout=1)
        delete_thread.start()
        assert observed_lock.second_acquire_attempted.wait(timeout=1)
        assert delete_done.is_set() is False
        assert session.closed is False
    finally:
        release.set()
        operation_thread.join(timeout=2)
        delete_thread.join(timeout=2)

    assert operation_thread.is_alive() is False
    assert delete_thread.is_alive() is False
    assert operation_done.is_set() is True
    assert delete_done.is_set() is True
    assert deleted == [True]
    assert session.is_closed()
    assert errors == []


def test_ttl_cleanup_does_not_close_a_session_while_it_is_acquired() -> None:
    clock = Clock()
    sessions: list[EmptySession] = []

    def session_factory() -> ChatSession:
        session = EmptySession()
        sessions.append(session)
        return cast(ChatSession, session)

    store = InMemorySessionStore(session_factory, ttl_seconds=10, clock=clock)
    session_id, entry = store.create()
    expiring_session = sessions[0]
    observed_lock = ObservedRLock()
    entry.lock = cast(Any, observed_lock)
    acquired = threading.Event()
    release = threading.Event()
    operation_done = threading.Event()
    create_done = threading.Event()
    created_ids: list[str] = []
    errors: list[BaseException] = []

    def hold_operation() -> None:
        try:
            with store.acquire(session_id):
                acquired.set()
                if not release.wait(timeout=2):
                    raise AssertionError("test did not release acquired operation")
                if expiring_session.closed:
                    raise AssertionError("TTL cleanup closed an acquired session")
        except BaseException as exc:  # pragma: no cover - surfaced by assertions below
            errors.append(exc)
        finally:
            operation_done.set()

    def create_session() -> None:
        try:
            new_session_id, _entry = store.create()
            created_ids.append(new_session_id)
        except BaseException as exc:  # pragma: no cover - surfaced by assertions below
            errors.append(exc)
        finally:
            create_done.set()

    operation_thread = threading.Thread(target=hold_operation)
    create_thread = threading.Thread(target=create_session)
    operation_thread.start()
    try:
        assert acquired.wait(timeout=1)
        clock.value = 11
        create_thread.start()
        assert observed_lock.second_acquire_attempted.wait(timeout=1)
        assert create_done.is_set() is False
        assert expiring_session.closed is False
    finally:
        release.set()
        operation_thread.join(timeout=2)
        create_thread.join(timeout=2)

    assert operation_thread.is_alive() is False
    assert create_thread.is_alive() is False
    assert operation_done.is_set() is True
    assert create_done.is_set() is True
    assert len(created_ids) == 1
    assert created_ids[0] != session_id
    assert len(sessions) == 2
    assert expiring_session.is_closed()
    assert not sessions[1].is_closed()
    assert errors == []
