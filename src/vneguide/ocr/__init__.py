"""Local, suggestion-only OCR support for the reviewed CT01 hero form."""

from .config import OcrConfig, load_ocr_config
from .errors import OcrBackendError, OcrError, OcrInputError
from .mapper import CT01TemplateMapper
from .models import (
    DocumentPreprocessor,
    OcrBackend,
    OcrBlock,
    OcrCandidate,
    OcrCandidateSink,
    OcrDocument,
    OcrMappingResult,
    OcrResult,
    PreparedPage,
)
from .preprocess import SafeDocumentPreprocessor
from .provider import QwenVisionBackend
from .service import OcrService

__all__ = [
    "CT01TemplateMapper",
    "DocumentPreprocessor",
    "OcrBackend",
    "OcrBackendError",
    "OcrBlock",
    "OcrCandidate",
    "OcrCandidateSink",
    "OcrConfig",
    "OcrDocument",
    "OcrError",
    "OcrInputError",
    "OcrMappingResult",
    "OcrResult",
    "OcrService",
    "PreparedPage",
    "SafeDocumentPreprocessor",
    "QwenVisionBackend",
    "load_ocr_config",
]
