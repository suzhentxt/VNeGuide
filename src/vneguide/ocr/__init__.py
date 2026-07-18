"""Public document-validation OCR API."""

from .config import OcrConfig, load_ocr_config
from .errors import OcrBackendError, OcrError, OcrInputError
from .models import (
    CheckResult,
    DocumentCheck,
    DocumentKind,
    DocumentPreprocessor,
    DocumentValidationBackend,
    ModelAssessment,
    OcrDocument,
    OcrResult,
    OcrStatus,
    PreparedPage,
)
from .preprocess import SafeDocumentPreprocessor
from .provider import OpenAIDocumentValidationBackend
from .service import OcrService

__all__ = [
    "CheckResult",
    "DocumentCheck",
    "DocumentKind",
    "DocumentPreprocessor",
    "DocumentValidationBackend",
    "ModelAssessment",
    "OcrBackendError",
    "OcrConfig",
    "OcrDocument",
    "OcrError",
    "OcrInputError",
    "OcrResult",
    "OcrService",
    "OcrStatus",
    "OpenAIDocumentValidationBackend",
    "PreparedPage",
    "SafeDocumentPreprocessor",
    "load_ocr_config",
]
