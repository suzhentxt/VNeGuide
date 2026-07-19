from __future__ import annotations

from pathlib import Path

import pytest

from vneguide.cli.runtime import load_session_factory
from vneguide.domain import NextAction, ProcedureCode


def _birth_certificate_payload() -> dict[str, object]:
    """Scripted extraction outcome routing to BIRTH_CERTIFICATE_COPY."""

    return {
        "classification": "supported",
        "procedure_code": "2.000635",
        "reply": None,
        "clarification_question": None,
        "fields": [],
        "context_signals": [],
        "information_request": None,
    }


def test_default_core_factory_is_loadable_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VNEGUIDE_LLM_ENV_FILE", raising=False)
    monkeypatch.setenv("VNEGUIDE_LLM_PROVIDER", "mock")
    monkeypatch.delenv("VNEGUIDE_MODEL", raising=False)
    monkeypatch.delenv("VNEGUIDE_API_KEY", raising=False)
    monkeypatch.delenv("VNEGUIDE_LITELLM_API_KEY", raising=False)
    factory = load_session_factory()
    session = factory(mock_responses=[_birth_certificate_payload()])
    result = session.send("Tôi cần xin lại giấy khai sinh")
    # Turn 1 routes to the pending procedure and asks for confirmation;
    # draft.procedure_code is only set after the user confirms.
    assert result.next_action is NextAction.CONFIRM_PROCEDURE
    assert result.state.pending_procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert result.state.draft.procedure_code is None
    close = getattr(session, "close", None)
    assert callable(close)
    close()


def test_default_core_factory_loads_an_explicit_llm_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("VNEGUIDE_LLM_PROVIDER=mock\n", encoding="utf-8")
    for name in (
        "VNEGUIDE_LLM_PROVIDER",
        "VNEGUIDE_MODEL",
        "VNEGUIDE_API_KEY",
        "VNEGUIDE_LITELLM_API_KEY",
        "VNEGUIDE_LITELLM_BASE_URL",
        "VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP",
        "VNEGUIDE_LITELLM_DISABLE_THINKING",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("VNEGUIDE_LLM_ENV_FILE", str(env_file))

    session = load_session_factory()(mock_responses=[_birth_certificate_payload()])
    result = session.send("Tôi cần xin lại giấy khai sinh")

    assert result.next_action is NextAction.CONFIRM_PROCEDURE
    assert result.state.pending_procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    assert result.state.draft.procedure_code is None
    close = getattr(session, "close", None)
    assert callable(close)
    close()
