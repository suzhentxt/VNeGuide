from __future__ import annotations

from collections.abc import Sequence

from vneguide.ocr import (
    DocumentCheck,
    DocumentKind,
    ModelAssessment,
    OcrBackendError,
    OcrDocument,
    OcrService,
    PreparedPage,
)


class StubPreprocessor:
    def prepare(self, _document: OcrDocument) -> tuple[PreparedPage, ...]:
        return (PreparedPage(1, b"jpeg", 100, 100),)


class StubBackend:
    def __init__(self, assessment: ModelAssessment | None = None, *, error: bool = False) -> None:
        self.assessment = assessment
        self.error = error

    def assess(self, _kind: DocumentKind, _pages: Sequence[PreparedPage]) -> ModelAssessment:
        if self.error:
            raise OcrBackendError("provider_timeout", "safe")
        assert self.assessment is not None
        return self.assessment


def assessment(
    kind: DocumentKind,
    *,
    result: str = "pass",
    confidence: float = 0.95,
) -> ModelAssessment:
    codes = ("name_valid", "date_valid")
    return ModelAssessment(
        tuple(DocumentCheck(code, result, confidence) for code in codes),  # type: ignore[arg-type]
        confidence,
    )


def test_clear_relevant_document_passes() -> None:
    service = OcrService(StubPreprocessor(), StubBackend(assessment("legal_dwelling")))
    result = service.validate_document("legal_dwelling", OcrDocument(b"x", "image/png"))
    assert result.status == "pass"
    assert result.error_code is None


def test_document_below_strict_confidence_does_not_pass() -> None:
    service = OcrService(
        StubPreprocessor(), StubBackend(assessment("legal_dwelling", confidence=0.79))
    )
    result = service.validate_document("legal_dwelling", OcrDocument(b"x", "image/png"))
    assert result.status == "needs_review"


def test_document_at_strict_confidence_threshold_passes() -> None:
    service = OcrService(
        StubPreprocessor(), StubBackend(assessment("legal_dwelling", confidence=0.80))
    )
    result = service.validate_document("legal_dwelling", OcrDocument(b"x", "image/png"))
    assert result.status == "pass"


def test_clear_wrong_document_fails() -> None:
    wrong = assessment("minor_consent")
    checks = list(wrong.checks)
    checks[0] = DocumentCheck("name_valid", "fail", 0.95)
    service = OcrService(StubPreprocessor(), StubBackend(ModelAssessment(tuple(checks), 0.95)))
    result = service.validate_document("minor_consent", OcrDocument(b"x", "image/png"))
    assert result.status == "fail"


def test_ambiguous_or_provider_failure_requires_review() -> None:
    ambiguous = OcrService(
        StubPreprocessor(), StubBackend(assessment("minor_consent", confidence=0.70))
    ).validate_document("minor_consent", OcrDocument(b"x", "image/png"))
    unavailable = OcrService(StubPreprocessor(), StubBackend(error=True)).validate_document(
        "legal_dwelling", OcrDocument(b"x", "image/png")
    )
    assert ambiguous.status == "needs_review"
    assert unavailable.status == "needs_review"
    assert unavailable.error_code == "provider_timeout"
