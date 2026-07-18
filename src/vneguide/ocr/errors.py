"""Typed, PII-safe OCR failures."""

from __future__ import annotations


class OcrError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class OcrInputError(OcrError):
    pass


class OcrBackendError(OcrError):
    pass


__all__ = ["OcrBackendError", "OcrError", "OcrInputError"]
