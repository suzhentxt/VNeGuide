"""PII-safe contracts for document validation OCR."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

DocumentKind = Literal["legal_dwelling", "minor_consent"]
CheckResult = Literal["pass", "uncertain", "fail"]
OcrStatus = Literal["pass", "needs_review", "fail"]


@dataclass(frozen=True, slots=True)
class OcrDocument:
    content: bytes
    declared_mime: str

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("OCR document must not be empty")
        if not self.declared_mime.strip():
            raise ValueError("OCR document MIME type must not be empty")


@dataclass(frozen=True, slots=True)
class PreparedPage:
    page_number: int
    jpeg_content: bytes
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.page_number < 1 or self.width < 1 or self.height < 1:
            raise ValueError("Prepared OCR page metadata is invalid")
        if not self.jpeg_content:
            raise ValueError("Prepared OCR page must contain image data")


@dataclass(frozen=True, slots=True)
class DocumentCheck:
    code: str
    result: CheckResult
    confidence: float

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("Document check code must not be empty")
        if self.result not in {"pass", "uncertain", "fail"}:
            raise ValueError("Document check result is invalid")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Document check confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ModelAssessment:
    checks: tuple[DocumentCheck, ...]
    overall_confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.overall_confidence <= 1.0:
            raise ValueError("Assessment confidence must be between 0 and 1")
        if len({check.code for check in self.checks}) != len(self.checks):
            raise ValueError("Assessment contains duplicate check codes")
        object.__setattr__(self, "checks", tuple(self.checks))


@dataclass(frozen=True, slots=True)
class OcrResult:
    status: OcrStatus
    document_kind: DocumentKind
    checks: tuple[DocumentCheck, ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)
    error_code: str | None = None
    duration_ms: int = 0

    def __post_init__(self) -> None:
        if self.status not in {"pass", "needs_review", "fail"}:
            raise ValueError("OCR result status is invalid")
        if self.duration_ms < 0:
            raise ValueError("OCR duration must not be negative")
        object.__setattr__(self, "checks", tuple(self.checks))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class DocumentPreprocessor(Protocol):
    def prepare(self, document: OcrDocument) -> tuple[PreparedPage, ...]: ...


class DocumentValidationBackend(Protocol):
    def assess(
        self,
        document_kind: DocumentKind,
        pages: Sequence[PreparedPage],
    ) -> ModelAssessment: ...


__all__ = [
    "CheckResult",
    "DocumentCheck",
    "DocumentKind",
    "DocumentPreprocessor",
    "DocumentValidationBackend",
    "ModelAssessment",
    "OcrDocument",
    "OcrResult",
    "OcrStatus",
    "PreparedPage",
]
