"""Vietnamese dialect and speech-transcript normalization."""

from .evaluation import (
    DialectEvaluationSample,
    NormalizationEvaluationMetrics,
    evaluate_normalizer,
    load_dialect_samples,
)
from .glossary import Glossary, GlossaryEntry, default_glossary
from .models import (
    Ambiguity,
    InputSource,
    ModelNormalizationCandidate,
    NormalizationResult,
    ProtectedKind,
    ProtectedSpan,
    SpanMapping,
)
from .normalizer import (
    LanguageNormalizer,
    ModelNormalizationUnavailable,
    ProviderModelNormalizer,
)
from .protected_spans import detect_protected_spans

__all__ = [
    "Ambiguity",
    "DialectEvaluationSample",
    "Glossary",
    "GlossaryEntry",
    "InputSource",
    "LanguageNormalizer",
    "ModelNormalizationCandidate",
    "ModelNormalizationUnavailable",
    "NormalizationResult",
    "NormalizationEvaluationMetrics",
    "ProtectedKind",
    "ProtectedSpan",
    "ProviderModelNormalizer",
    "SpanMapping",
    "default_glossary",
    "detect_protected_spans",
    "evaluate_normalizer",
    "load_dialect_samples",
]
