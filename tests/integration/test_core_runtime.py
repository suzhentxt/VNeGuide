from __future__ import annotations

from vneguide.cli.runtime import load_session_factory
from vneguide.domain import NextAction


def test_default_core_factory_is_loadable_without_api_key() -> None:
    factory = load_session_factory()
    session = factory()
    result = session.send("Tôi cần xin lại giấy khai sinh")
    assert result.next_action is NextAction.RETRY
    close = getattr(session, "close", None)
    assert callable(close)
    close()
