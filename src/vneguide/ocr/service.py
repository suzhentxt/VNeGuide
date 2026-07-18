"""OCR application service independent of HTTP and conversation state."""

from __future__ import annotations

import time
from collections.abc import Callable

from vneguide.data import ProcedureRepository
from vneguide.domain import JSONValue, ProcedureCode
from vneguide.rules import RuleEngine

from .errors import OcrBackendError
from .mapper import CT01TemplateMapper
from .models import DocumentPreprocessor, OcrBackend, OcrDocument, OcrResult


class OcrService:
    def __init__(
        self,
        preprocessor: DocumentPreprocessor,
        backend: OcrBackend,
        repository: ProcedureRepository,
        *,
        mapper: CT01TemplateMapper | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._preprocessor = preprocessor
        self._backend = backend
        self._rules = RuleEngine(repository)
        self._mapper = mapper or CT01TemplateMapper()
        self._clock = clock

    def extract_ct01(self, document: OcrDocument) -> OcrResult:
        started = self._clock()
        pages = self._preprocessor.prepare(document)
        try:
            blocks = self._backend.extract(pages)
        except OcrBackendError as exc:
            return OcrResult(
                status="manual_input",
                document_type="uncertain",
                error_code=exc.code,
                warnings=("manual_input_available",),
                duration_ms=self._duration(started),
            )
        mapped = self._mapper.map(blocks, validate_value=self._validate_value)
        if mapped.document_type != "CT01":
            return OcrResult(
                status="manual_input",
                document_type=mapped.document_type,
                error_code="wrong_document_type",
                warnings=mapped.warnings + ("manual_input_available",),
                duration_ms=self._duration(started),
            )
        if not mapped.candidates:
            return OcrResult(
                status="manual_input",
                document_type="CT01",
                error_code="no_fields_recognized",
                warnings=mapped.warnings + ("manual_input_available",),
                duration_ms=self._duration(started),
            )
        return OcrResult(
            status="succeeded",
            document_type="CT01",
            candidates=mapped.candidates,
            warnings=mapped.warnings,
            duration_ms=self._duration(started),
        )

    def _validate_value(self, field_id: str, value: JSONValue) -> None:
        self._rules.validate_field_value(
            ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
            field_id,
            value,
        )

    def _duration(self, started: float) -> int:
        return max(0, round((self._clock() - started) * 1_000))


__all__ = ["OcrService"]
