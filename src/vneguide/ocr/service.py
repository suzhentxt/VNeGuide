"""Deterministic, permissive decision layer for document validation OCR."""

from __future__ import annotations

import time

from .errors import OcrBackendError
from .models import (
    DocumentKind,
    DocumentPreprocessor,
    DocumentValidationBackend,
    OcrDocument,
    OcrResult,
    OcrStatus,
)

PASS_CONFIDENCE = 0.75
CLEAR_MISMATCH_CONFIDENCE = 0.90

_REQUIRED_CHECKS: dict[DocumentKind, frozenset[str]] = {
    "legal_dwelling": frozenset(
        {
            "document_type_match",
            "readable_content",
            "dwelling_location_present",
            "dwelling_relationship_present",
        }
    ),
    "minor_consent": frozenset(
        {
            "document_type_match",
            "readable_content",
            "consent_statement_present",
            "parent_guardian_role_present",
        }
    ),
}


class OcrService:
    def __init__(
        self,
        preprocessor: DocumentPreprocessor,
        backend: DocumentValidationBackend,
    ) -> None:
        self._preprocessor = preprocessor
        self._backend = backend

    def validate_document(
        self,
        document_kind: DocumentKind,
        document: OcrDocument,
    ) -> OcrResult:
        started = time.monotonic()
        pages = self._preprocessor.prepare(document)
        try:
            assessment = self._backend.assess(document_kind, pages)
        except OcrBackendError as exc:
            return OcrResult(
                status="needs_review",
                document_kind=document_kind,
                warnings=("official_review_required",),
                error_code=exc.code,
                duration_ms=_duration_ms(started),
            )

        checks = {check.code: check for check in assessment.checks}
        type_check = checks.get("document_type_match")
        if (
            type_check is not None
            and type_check.result == "fail"
            and type_check.confidence >= CLEAR_MISMATCH_CONFIDENCE
        ):
            decision: OcrStatus = "fail"
            warnings: tuple[str, ...] = ("replace_wrong_document",)
        elif (
            assessment.overall_confidence >= PASS_CONFIDENCE
            and _REQUIRED_CHECKS[document_kind].issubset(checks)
            and all(
                checks[code].result == "pass" and checks[code].confidence >= PASS_CONFIDENCE
                for code in _REQUIRED_CHECKS[document_kind]
            )
        ):
            decision = "pass"
            warnings = ()
        else:
            decision = "needs_review"
            warnings = ("official_review_required",)

        return OcrResult(
            status=decision,
            document_kind=document_kind,
            checks=assessment.checks,
            warnings=warnings,
            duration_ms=_duration_ms(started),
        )


def _duration_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1_000))


__all__ = ["CLEAR_MISMATCH_CONFIDENCE", "OcrService", "PASS_CONFIDENCE"]
