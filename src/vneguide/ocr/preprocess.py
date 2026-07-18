"""Bounded in-memory image and PDF preprocessing for OCR."""

from __future__ import annotations

import importlib
import io
import math
import warnings
from typing import Any

from .errors import OcrInputError
from .models import OcrDocument, PreparedPage

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_PAGES = 2
MAX_PIXELS = 20_000_000
MAX_LONG_EDGE = 2_048
PDF_RENDER_DPI = 180
ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "application/pdf"})


def _actual_mime(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    return None


class SafeDocumentPreprocessor:
    """Validate and normalize uploads without persisting their contents."""

    def prepare(self, document: OcrDocument) -> tuple[PreparedPage, ...]:
        declared_mime = document.declared_mime.split(";", 1)[0].strip().lower()
        if declared_mime not in ALLOWED_MIME_TYPES:
            raise OcrInputError("unsupported_mime", "Loại tệp không được hỗ trợ.")
        if len(document.content) > MAX_FILE_BYTES:
            raise OcrInputError("file_too_large", "Tệp vượt quá giới hạn 8 MiB.")
        actual_mime = _actual_mime(document.content)
        if actual_mime is None or actual_mime != declared_mime:
            raise OcrInputError("mime_mismatch", "Nội dung tệp không khớp MIME đã khai báo.")
        if actual_mime == "application/pdf":
            return self._prepare_pdf(document.content)
        return (self._prepare_image(document.content, page_number=1),)

    def _prepare_image(self, content: bytes, *, page_number: int) -> PreparedPage:
        try:
            image_module = importlib.import_module("PIL.Image")
            image_ops = importlib.import_module("PIL.ImageOps")
        except ImportError:
            raise OcrInputError(
                "ocr_dependency_missing", "Thiếu dependency xử lý ảnh của OCR."
            ) from None

        bomb_warning = image_module.DecompressionBombWarning
        bomb_error = image_module.DecompressionBombError
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", bomb_warning)
                with image_module.open(io.BytesIO(content)) as opened:
                    if getattr(opened, "n_frames", 1) != 1:
                        raise OcrInputError(
                            "multiple_image_frames", "Ảnh nhiều khung hình không được hỗ trợ."
                        )
                    width, height = opened.size
                    if width * height > MAX_PIXELS:
                        raise OcrInputError("too_many_pixels", "Ảnh có độ phân giải quá lớn.")
                    opened.load()
                    normalized = image_ops.exif_transpose(opened).convert("RGB")
                    normalized.thumbnail((MAX_LONG_EDGE, MAX_LONG_EDGE))
                    output = io.BytesIO()
                    normalized.save(output, format="JPEG", quality=88, optimize=True)
                    final_width, final_height = normalized.size
        except OcrInputError:
            raise
        except (bomb_warning, bomb_error):
            raise OcrInputError("too_many_pixels", "Ảnh có độ phân giải quá lớn.") from None
        except (OSError, ValueError):
            raise OcrInputError("corrupt_image", "Không thể đọc ảnh tải lên.") from None
        return PreparedPage(
            page_number=page_number,
            jpeg_content=output.getvalue(),
            width=final_width,
            height=final_height,
        )

    def _prepare_pdf(self, content: bytes) -> tuple[PreparedPage, ...]:
        try:
            pdfium = importlib.import_module("pypdfium2")
        except ImportError:
            raise OcrInputError(
                "ocr_dependency_missing", "Thiếu dependency raster PDF của OCR."
            ) from None
        document: Any | None = None
        try:
            document = pdfium.PdfDocument(content)
            page_count = len(document)
            if page_count < 1:
                raise OcrInputError("empty_pdf", "PDF không có trang.")
            if page_count > MAX_PAGES:
                raise OcrInputError("too_many_pages", "PDF vượt quá giới hạn 2 trang.")
            pages: list[PreparedPage] = []
            scale = PDF_RENDER_DPI / 72
            for index in range(page_count):
                page = document[index]
                try:
                    width_points, height_points = page.get_size()
                    if width_points <= 0 or height_points <= 0:
                        raise OcrInputError("corrupt_pdf", "Trang PDF có kích thước không hợp lệ.")
                    safe_scale = min(
                        scale,
                        MAX_LONG_EDGE / max(width_points, height_points),
                        math.sqrt(MAX_PIXELS / (width_points * height_points)),
                    )
                    bitmap = page.render(scale=safe_scale)
                    image = bitmap.to_pil()
                    output = io.BytesIO()
                    image.convert("RGB").save(output, format="JPEG", quality=88, optimize=True)
                    pages.append(self._prepare_image(output.getvalue(), page_number=index + 1))
                finally:
                    page.close()
            return tuple(pages)
        except OcrInputError:
            raise
        except Exception as exc:
            if type(exc).__module__.startswith("pypdfium2"):
                raise OcrInputError("corrupt_pdf", "Không thể đọc PDF tải lên.") from None
            raise
        finally:
            if document is not None:
                document.close()


__all__ = [
    "ALLOWED_MIME_TYPES",
    "MAX_FILE_BYTES",
    "MAX_LONG_EDGE",
    "MAX_PAGES",
    "MAX_PIXELS",
    "SafeDocumentPreprocessor",
]
