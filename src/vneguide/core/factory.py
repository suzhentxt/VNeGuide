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
from vneguide.memory import LongTermMemory, build_memory, load_memory_config

from .session import ConversationSession


def _try_build_deep_session(
    repository: ProcedureRepository,
    extractor: StructuredExtractor,
    responder: GroundedResponder,
    compactor: MemoryCompactor,
    long_term_memory: LongTermMemory | None,
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
        long_term_memory=long_term_memory,
    )


def create_session() -> ConversationSession:
    repository = ProcedureRepository.discover()
    catalog = ExtractionCatalog.from_data_package(repository.paths.root)
    provider = build_llm_provider(load_llm_config(env_file=os.environ.get("VNEGUIDE_LLM_ENV_FILE")))
    extractor = StructuredExtractor(provider, catalog)
    responder = GroundedResponder(provider, repository)
    compactor = MemoryCompactor(provider)
    long_term_memory = build_memory(load_memory_config())

    deep = _try_build_deep_session(
        repository,
        extractor,
        responder,
        compactor,
        long_term_memory,
    )
    if deep is not None:
        return deep
    return ConversationSession(
        extractor,
        repository,
        responder=responder,
        compactor=compactor,
        long_term_memory=long_term_memory,
    )
