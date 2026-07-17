from __future__ import annotations


class StubSession:
    def send(self, _message: str) -> object:
        return object()


def create_session() -> StubSession:
    return StubSession()
