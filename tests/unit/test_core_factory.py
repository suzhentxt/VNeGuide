from __future__ import annotations

from pathlib import Path

import pytest

from vneguide.core import CatalogReplyComposer
from vneguide.core.factory import _llm_env_file, create_session

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("variant", "guided"),
    (
        (None, True),
        ("guided", True),
        ("baseline", False),
    ),
)
def test_factory_selects_configured_chat_core_variant(
    monkeypatch: pytest.MonkeyPatch,
    variant: str | None,
    guided: bool,
) -> None:
    monkeypatch.chdir(ROOT)
    monkeypatch.delenv("VNEGUIDE_LLM_ENV_FILE", raising=False)
    monkeypatch.setenv("VNEGUIDE_LLM_PROVIDER", "mock")
    monkeypatch.setenv("VNEGUIDE_MODEL", "mock-scripted")
    if variant is None:
        monkeypatch.delenv("VNEGUIDE_CHAT_CORE_VARIANT", raising=False)
    else:
        monkeypatch.setenv("VNEGUIDE_CHAT_CORE_VARIANT", variant)

    session = create_session()

    composer = session._reply_composer  # noqa: SLF001 - composition-root assertion
    assert isinstance(composer, CatalogReplyComposer) is guided


def test_factory_rejects_unknown_chat_core_variant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(ROOT)
    monkeypatch.delenv("VNEGUIDE_LLM_ENV_FILE", raising=False)
    monkeypatch.setenv("VNEGUIDE_LLM_PROVIDER", "mock")
    monkeypatch.setenv("VNEGUIDE_MODEL", "mock-scripted")
    monkeypatch.setenv("VNEGUIDE_CHAT_CORE_VARIANT", "free-form")

    with pytest.raises(ValueError, match="baseline or guided"):
        create_session()


def test_factory_discovers_ignored_local_env_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VNEGUIDE_LLM_ENV_FILE", raising=False)

    assert _llm_env_file() is None
    (tmp_path / ".env").write_text("VNEGUIDE_LLM_PROVIDER=mock\n", encoding="utf-8")

    assert _llm_env_file() == Path(".env")


def test_factory_explicit_env_file_wins_over_local_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("VNEGUIDE_LLM_PROVIDER=mock\n", encoding="utf-8")
    monkeypatch.setenv("VNEGUIDE_LLM_ENV_FILE", "/run/secrets/vneguide.env")

    assert _llm_env_file() == "/run/secrets/vneguide.env"
