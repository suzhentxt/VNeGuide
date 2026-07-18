"""Default composition root used by the CLI and API."""

from __future__ import annotations

import os

from vneguide.ai import (
    ExtractionCatalog,
    GroundedResponder,
    MemoryCompactor,
    StructuredExtractor,
    build_llm_provider,
    load_llm_config,
)
from vneguide.data import ProcedureRepository

from .session import ConversationSession


def _try_build_deep_session(
    repository: ProcedureRepository,
    extractor: StructuredExtractor,
    responder: GroundedResponder,
    compactor: MemoryCompactor,
) -> ConversationSession | None:
    """Build a ``DeepAgentSession`` if langchain/deepagents are installed.

    Returns ``None`` when the agent extras are not installed (stdlib-only env),
    so callers fall back to :class:`ConversationSession`.
    """

    try:
        from ..agent.session_adapter import DeepAgentSession
        from ..ai.config import load_llm_config as _load_config
        from ..ai.providers.langchain_chat import build_chat_model
    except ImportError:
        return None

    config = _load_config(env_file=os.environ.get("VNEGUIDE_LLM_ENV_FILE"))
    model = build_chat_model(config)
    return DeepAgentSession(
        model,
        extractor,
        repository,
        responder=responder,
        compactor=compactor,
    )


def create_session() -> ConversationSession:
    repository = ProcedureRepository.discover()
    catalog = ExtractionCatalog.from_data_package(repository.paths.root)
    provider = build_llm_provider(load_llm_config(env_file=os.environ.get("VNEGUIDE_LLM_ENV_FILE")))
    extractor = StructuredExtractor(provider, catalog)
    responder = GroundedResponder(provider, repository)
    compactor = MemoryCompactor(provider)

    deep = _try_build_deep_session(repository, extractor, responder, compactor)
    if deep is not None:
        return deep
    return ConversationSession(
        extractor,
        repository,
        responder=responder,
        compactor=compactor,
    )
