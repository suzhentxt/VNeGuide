from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from vneguide.ocr import CT01TemplateMapper, OcrBlock

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "ocr" / "ct01_blocks.json"


def _accept(_field_id: str, _value: Any) -> None:
    return None


def test_ct01_adapter_fixture_field_recall_and_latency() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    expected_total = 0
    correct_total = 0
    emitted_total = 0
    started = time.perf_counter()
    for case in payload["cases"]:
        blocks = tuple(
            OcrBlock(
                "text",
                (0.05, index * 0.1, 0.95, index * 0.1 + 0.05),
                line["angle"],
                line["text"],
            )
            for index, line in enumerate(case["lines"])
        )
        result = CT01TemplateMapper().map(blocks, validate_value=_accept)
        assert result.document_type == case["expected_document_type"], case["case_id"]
        actual = {candidate.field_id: candidate.suggested_value for candidate in result.candidates}
        expected = case["expected_fields"]
        expected_total += len(expected)
        emitted_total += len(actual)
        correct_total += sum(actual.get(field_id) == value for field_id, value in expected.items())

    duration_ms = (time.perf_counter() - started) * 1_000
    field_recall = correct_total / expected_total
    field_precision = correct_total / emitted_total
    assert field_recall >= 0.90
    assert field_precision == 1.0
    assert duration_ms < 100.0
