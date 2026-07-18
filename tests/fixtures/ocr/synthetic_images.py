"""Build small in-memory document images for upload-boundary tests."""

from __future__ import annotations

import importlib
import io
from typing import Any, Literal


def build_image(
    condition: Literal["clear", "blurred", "rotated", "wrong_document"],
    *,
    image_module: Any,
    image_filter_module: Any,
) -> bytes:
    image = image_module.new("RGB", (800, 500), "white")
    image_draw = importlib.import_module("PIL.ImageDraw")
    image_font = importlib.import_module("PIL.ImageFont")
    draw = image_draw.Draw(image)
    font = image_font.load_default(size=28)
    if condition == "wrong_document":
        draw.text((40, 60), "SYNTHETIC RECEIPT - NOT CT01", fill="black", font=font)
    else:
        draw.text((40, 60), "CT01 - SYNTHETIC FORM", fill="black", font=font)
        draw.text((40, 130), "FULL NAME: TEST USER", fill="black", font=font)
    if condition == "blurred":
        image = image.filter(image_filter_module.GaussianBlur(radius=2.0))
    elif condition == "rotated":
        image = image.rotate(90, expand=True)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


__all__ = ["build_image"]
