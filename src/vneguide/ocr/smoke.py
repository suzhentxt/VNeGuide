"""Live Qwen OCR smoke using an in-memory synthetic CT01 image."""

from __future__ import annotations

import argparse
import importlib
import io
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vneguide.ai.config import load_llm_config
from vneguide.data import ProcedureRepository

from .models import OcrDocument
from .preprocess import SafeDocumentPreprocessor
from .provider import QwenVisionBackend
from .service import OcrService

_SYNTHETIC_PERSONAL_ID = "0" * 12
_EXPECTED_FIELDS = {
    "applicant_full_name": "NGƯỜI DÙNG THỬ NGHIỆM",
    "applicant_date_of_birth": "2000-01-01",
    "applicant_personal_id": _SYNTHETIC_PERSONAL_ID,
    "temporary_address": "Số 00 đường Kiểm Thử, Hà Nội",
}

_VISIBLE_LINES = (
    "Mẫu CT01",
    "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ",
    "Họ, chữ đệm và tên: NGƯỜI DÙNG THỬ NGHIỆM",
    "Ngày, tháng, năm sinh: 01/01/2000",
    f"Số định danh cá nhân: {_SYNTHETIC_PERSONAL_ID}",
    "Đăng ký tạm trú tại: Số 00 đường Kiểm Thử, Hà Nội",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run live Qwen OCR on a synthetic CT01")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--confirm-live", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.confirm_live:
        raise SystemExit("--confirm-live is required")
    if args.runs < 1 or args.runs > 10:
        raise SystemExit("--runs must be between 1 and 10")
    if args.timeout_seconds < 1 or args.timeout_seconds > 300:
        raise SystemExit("--timeout-seconds must be between 1 and 300")

    llm_config = load_llm_config(env_file=Path(args.env_file))
    repository = ProcedureRepository.discover()
    document = _synthetic_document()
    runs: list[dict[str, Any]] = []
    correct_total = 0
    expected_total = len(_EXPECTED_FIELDS) * args.runs
    durations: list[int] = []
    for run_number in range(1, args.runs + 1):
        service = OcrService(
            SafeDocumentPreprocessor(),
            QwenVisionBackend(llm_config, timeout_seconds=args.timeout_seconds),
            repository,
        )
        result = service.extract_ct01(document)
        actual = {candidate.field_id: candidate.suggested_value for candidate in result.candidates}
        correct = sum(
            actual.get(field_id) == expected for field_id, expected in _EXPECTED_FIELDS.items()
        )
        correct_total += correct
        durations.append(result.duration_ms)
        runs.append(
            {
                "run": run_number,
                "status": result.status,
                "document_type": result.document_type,
                "correct_fields": correct,
                "expected_fields": len(_EXPECTED_FIELDS),
                "error_code": result.error_code,
                "duration_ms": result.duration_ms,
            }
        )
    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "model": llm_config.model,
        "fixture": "synthetic_ct01_clear",
        "runs": runs,
        "field_recall": round(correct_total / expected_total, 4),
        "average_latency_ms": round(sum(durations) / len(durations)),
        "max_latency_ms": max(durations),
    }
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0 if correct_total == expected_total else 1


def _synthetic_document() -> OcrDocument:
    try:
        image_module = importlib.import_module("PIL.Image")
        image_draw = importlib.import_module("PIL.ImageDraw")
        image_font = importlib.import_module("PIL.ImageFont")
    except ImportError:
        raise SystemExit("Install Pillow before running the OCR smoke") from None
    image = image_module.new("RGB", (1_800, 1_200), "white")
    draw = image_draw.Draw(image)
    try:
        font = image_font.truetype(r"C:\Windows\Fonts\arial.ttf", 42)
    except OSError:
        font = image_font.load_default(size=32)
    y = 90
    for line in _VISIBLE_LINES:
        draw.text((90, y), line, fill="black", font=font)
        y += 150
    output = io.BytesIO()
    image.save(output, format="PNG")
    return OcrDocument(output.getvalue(), "image/png")


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
