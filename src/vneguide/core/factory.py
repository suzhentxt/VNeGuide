"""Default composition root used by the CLI."""

from __future__ import annotations

import os

from vneguide.ai import ExtractionCatalog, StructuredExtractor, build_llm_provider, load_llm_config
from vneguide.data import ProcedureRepository

from .replies import CatalogReplyComposer
from .session import ConversationSession


def create_session() -> ConversationSession:
    repository = ProcedureRepository.discover()
    catalog = ExtractionCatalog.from_data_package(repository.paths.root)
    provider = build_llm_provider(load_llm_config(env_file=os.environ.get("VNEGUIDE_LLM_ENV_FILE")))
    extractor = StructuredExtractor(provider, catalog)
    variant = os.environ.get("VNEGUIDE_CHAT_CORE_VARIANT", "guided").strip().lower()
    if variant not in {"baseline", "guided"}:
        raise ValueError("VNEGUIDE_CHAT_CORE_VARIANT must be baseline or guided")
    reply_composer = CatalogReplyComposer(repository) if variant == "guided" else None
    return ConversationSession(extractor, repository, reply_composer=reply_composer)
