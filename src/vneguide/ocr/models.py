"""Wire-neutral contracts for document OCR."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

from vneguide.domain import JSONValue, ProcedureCode, TurnResult

OcrStatus = Literal["succeeded", "manual_input"]
OcrDocumentType = Literal["CT01", "other", "uncertain"]


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
class OcrBlock:
    block_type: str
    bbox: tuple[float, float, float, float]
    angle: int | None
    content: str | None
    page_number: int = 1

    def __post_init__(self) -> None:
        if not self.block_type.strip():
            raise ValueError("OCR block type must not be empty")
        if len(self.bbox) != 4 or any(not 0.0 <= coordinate <= 1.0 for coordinate in self.bbox):
            raise ValueError("OCR block bbox must contain four normalized coordinates")
        if self.bbox[0] > self.bbox[2] or self.bbox[1] > self.bbox[3]:
            raise ValueError("OCR block bbox is inverted")
        if self.angle not in {None, 0, 90, 180, 270}:
            raise ValueError("OCR block angle is invalid")
        if self.page_number < 1:
            raise ValueError("OCR block page number must be positive")


@dataclass(frozen=True, slots=True)
class OcrCandidate:
    field_id: str
    suggested_value: JSONValue
    confidence: float
    evidence: str
    source: Literal["USER_UPLOAD"] = "USER_UPLOAD"

    def __post_init__(self) -> None:
        if not self.field_id.strip():
            raise ValueError("OCR candidate field_id must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("OCR candidate confidence must be between 0 and 1")
        if not self.evidence.strip() or len(self.evidence) > 500:
            raise ValueError("OCR candidate evidence must be short and non-empty")


@dataclass(frozen=True, slots=True)
class OcrResult:
    status: OcrStatus
    document_type: OcrDocumentType
    candidates: tuple[OcrCandidate, ...] = ()
    warnings: tuple[str, ...] = ()
    error_code: str | None = None
    duration_ms: int = 0

    def __post_init__(self) -> None:
        if self.duration_ms < 0:
            raise ValueError("OCR duration must not be negative")
        if self.status == "manual_input" and self.candidates:
            raise ValueError("Manual-input OCR result cannot contain candidates")
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "warnings", tuple(self.warnings))


@dataclass(frozen=True, slots=True)
class OcrMappingResult:
    document_type: OcrDocumentType
    document_confidence: float
    candidates: tuple[OcrCandidate, ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)


class DocumentPreprocessor(Protocol):
    def prepare(self, document: OcrDocument) -> tuple[PreparedPage, ...]: ...


class OcrBackend(Protocol):
    def extract(self, pages: Sequence[PreparedPage]) -> tuple[OcrBlock, ...]: ...


class OcrCandidateSink(Protocol):
    def propose_ocr_candidates(
        self,
        procedure_code: ProcedureCode,
        candidates: Sequence[OcrCandidate],
        *,
        expected_revision: int,
    ) -> TurnResult: ...


__all__ = [
    "DocumentPreprocessor",
    "OcrBackend",
    "OcrBlock",
    "OcrCandidate",
    "OcrCandidateSink",
    "OcrDocument",
    "OcrDocumentType",
    "OcrMappingResult",
    "OcrResult",
    "OcrStatus",
    "PreparedPage",
]
