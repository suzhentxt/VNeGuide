from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from vneguide.data import ProcedureRepository
from vneguide.ocr import OcrBlock, OcrDocument, OcrResult, OcrService, PreparedPage
from vneguide.ocr.errors import OcrBackendError

ROOT = Path(__file__).resolve().parents[2]


class StubPreprocessor:
    def prepare(self, _document: OcrDocument) -> tuple[PreparedPage, ...]:
        return (PreparedPage(1, b"jpeg", 100, 100),)


class StubBackend:
    def __init__(self, blocks: tuple[OcrBlock, ...]) -> None:
        self._blocks = blocks

    def extract(self, _pages: Sequence[PreparedPage]) -> tuple[OcrBlock, ...]:
        return self._blocks


class FailingBackend:
    def extract(self, _pages: Sequence[PreparedPage]) -> tuple[OcrBlock, ...]:
        raise OcrBackendError("inference_failed", "synthetic failure")


def _service(backend: StubBackend | FailingBackend) -> OcrService:
    return OcrService(StubPreprocessor(), backend, ProcedureRepository.discover(ROOT))


def test_service_validates_candidates_against_reviewed_catalog() -> None:
    blocks = (
        OcrBlock("text", (0.0, 0.0, 1.0, 0.1), 0, "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ"),
        OcrBlock("text", (0.0, 0.1, 1.0, 0.2), 0, "Mẫu CT01"),
        OcrBlock("text", (0.0, 0.2, 1.0, 0.3), 0, "Số định danh cá nhân: 000000000000"),
    )

    result = _service(StubBackend(blocks)).extract_ct01(OcrDocument(b"fake", "image/png"))

    assert result.status == "succeeded"
    assert [candidate.field_id for candidate in result.candidates] == ["applicant_personal_id"]


def test_backend_failure_returns_manual_input_without_candidates() -> None:
    result = _service(FailingBackend()).extract_ct01(OcrDocument(b"fake", "image/png"))

    assert result == OcrResult(
        status="manual_input",
        document_type="uncertain",
        warnings=("manual_input_available",),
        error_code="inference_failed",
        duration_ms=result.duration_ms,
    )
