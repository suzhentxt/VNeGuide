"""Default composition root used by the CLI."""

from __future__ import annotations

import os

from vneguide.ai import ExtractionCatalog, StructuredExtractor, build_llm_provider, load_llm_config
from vneguide.data import ProcedureRepository
from vneguide.language import LanguageNormalizer, ProviderModelNormalizer

from .replies import CatalogReplyComposer
from .session import ConversationSession


def create_session() -> ConversationSession:
    repository = ProcedureRepository.discover()
    catalog = ExtractionCatalog.from_data_package(repository.paths.root)
    llm_config = load_llm_config(env_file=os.environ.get("VNEGUIDE_LLM_ENV_FILE"))
    provider = build_llm_provider(llm_config)
    model_normalizer = (
        ProviderModelNormalizer(provider) if llm_config.language_model_assisted else None
    )
    extractor = StructuredExtractor(
        provider,
        catalog,
        normalizer=LanguageNormalizer(model_normalizer=model_normalizer),
    )
    variant = os.environ.get("VNEGUIDE_CHAT_CORE_VARIANT", "guided").strip().lower()
    if variant not in {"baseline", "guided"}:
        raise ValueError("VNEGUIDE_CHAT_CORE_VARIANT must be baseline or guided")
    reply_composer = CatalogReplyComposer(repository) if variant == "guided" else None
    return ConversationSession(extractor, repository, reply_composer=reply_composer)
