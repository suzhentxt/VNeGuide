from __future__ import annotations

import importlib
import io

import pytest

from tests.fixtures.ocr.synthetic_images import build_image
from vneguide.ocr import OcrDocument, SafeDocumentPreprocessor
from vneguide.ocr.errors import OcrInputError
from vneguide.ocr.preprocess import MAX_FILE_BYTES

image_module = pytest.importorskip("PIL.Image")
image_filter_module = pytest.importorskip("PIL.ImageFilter")


@pytest.mark.parametrize("condition", ["clear", "blurred", "rotated", "wrong_document"])
def test_synthetic_image_conditions_are_normalized_in_memory(condition: str) -> None:
    content = build_image(
        condition,  # type: ignore[arg-type]
        image_module=image_module,
        image_filter_module=image_filter_module,
    )

    pages = SafeDocumentPreprocessor().prepare(OcrDocument(content, "image/png"))

    assert len(pages) == 1
    assert pages[0].jpeg_content.startswith(b"\xff\xd8\xff")
    assert max(pages[0].width, pages[0].height) <= 2_048


def test_mime_spoof_is_rejected_before_decode() -> None:
    content = build_image(
        "clear",
        image_module=image_module,
        image_filter_module=image_filter_module,
    )

    with pytest.raises(OcrInputError) as caught:
        SafeDocumentPreprocessor().prepare(OcrDocument(content, "image/jpeg"))

    assert caught.value.code == "mime_mismatch"


def test_file_size_limit_fails_before_decode() -> None:
    content = b"%PDF-" + b"0" * MAX_FILE_BYTES
    with pytest.raises(OcrInputError) as caught:
        SafeDocumentPreprocessor().prepare(OcrDocument(content, "application/pdf"))
    assert caught.value.code == "file_too_large"


def test_single_page_pdf_is_rasterized_in_memory() -> None:
    pytest.importorskip("pypdfium2")
    image = image_module.new("RGB", (300, 200), "white")
    output = io.BytesIO()
    image.save(output, format="PDF")

    pages = SafeDocumentPreprocessor().prepare(OcrDocument(output.getvalue(), "application/pdf"))

    assert len(pages) == 1
    assert pages[0].jpeg_content.startswith(b"\xff\xd8\xff")


def test_pdf_page_limit_fails_closed() -> None:
    pytest.importorskip("pypdfium2")
    images = [image_module.new("RGB", (100, 100), "white") for _ in range(3)]
    output = io.BytesIO()
    images[0].save(output, format="PDF", save_all=True, append_images=images[1:])

    with pytest.raises(OcrInputError) as caught:
        SafeDocumentPreprocessor().prepare(OcrDocument(output.getvalue(), "application/pdf"))

    assert caught.value.code == "too_many_pages"


def test_missing_image_dependency_has_safe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    content = build_image(
        "clear",
        image_module=image_module,
        image_filter_module=image_filter_module,
    )
    real_import = importlib.import_module

    def missing_pillow(name: str) -> object:
        if name.startswith("PIL"):
            raise ImportError(name)
        return real_import(name)

    monkeypatch.setattr(importlib, "import_module", missing_pillow)
    with pytest.raises(OcrInputError) as caught:
        SafeDocumentPreprocessor().prepare(OcrDocument(content, "image/png"))
    assert caught.value.code == "ocr_dependency_missing"
