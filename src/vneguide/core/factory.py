"""Default composition root used by the CLI."""

from __future__ import annotations

import os

from vneguide.ai import ExtractionCatalog, StructuredExtractor, build_llm_provider, load_llm_config
from vneguide.data import ProcedureRepository

from .session import ConversationSession


def create_session() -> ConversationSession:
    repository = ProcedureRepository.discover()
    catalog = ExtractionCatalog.from_data_package(repository.paths.root)
    provider = build_llm_provider(load_llm_config(env_file=os.environ.get("VNEGUIDE_LLM_ENV_FILE")))
    extractor = StructuredExtractor(provider, catalog)
    return ConversationSession(extractor, repository)
