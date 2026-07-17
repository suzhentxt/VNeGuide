"""Tests for the dependency-free JSON Schema subset."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from vneguide.data import (
    DataFormatError,
    SchemaValidationError,
    assert_json_schema,
    load_json,
    validate_json_schema,
)


class SchemaValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "score", "status"],
            "properties": {
                "name": {"type": "string", "pattern": "^[A-Z]+$"},
                "score": {"type": "integer", "minimum": 0, "maximum": 100},
                "status": {"enum": ["approved", "stale"]},
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }

    def test_accepts_valid_document(self) -> None:
        self.assertEqual(
            validate_json_schema(
                {"name": "PACK", "score": 100, "status": "approved", "items": ["x"]},
                self.schema,
            ),
            (),
        )

    def test_reports_required_type_enum_pattern_bounds_and_extra_properties(self) -> None:
        violations = validate_json_schema(
            {
                "name": "lower",
                "score": 101,
                "status": "unknown",
                "items": [1],
                "extra": True,
            },
            self.schema,
        )
        messages = " | ".join(str(item) for item in violations)
        self.assertIn("pattern", messages)
        self.assertIn("at most", messages)
        self.assertIn("enum", messages)
        self.assertIn("expected type string", messages)
        self.assertIn("unexpected property", messages)

    def test_integer_does_not_accept_boolean(self) -> None:
        violations = validate_json_schema(
            {"name": "PACK", "score": True, "status": "approved"}, self.schema
        )
        self.assertTrue(any("integer" in item.message for item in violations))

    def test_number_must_be_finite(self) -> None:
        violations = validate_json_schema(float("nan"), {"type": "number"})
        self.assertEqual(violations[0].message, "must be a finite number")

    def test_assert_raises_aggregated_error(self) -> None:
        with self.assertRaises(SchemaValidationError) as context:
            assert_json_schema({}, self.schema)
        self.assertEqual(len(context.exception.violations), 3)

    def test_loader_rejects_nan_and_infinity(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            for constant in ("NaN", "Infinity", "-Infinity"):
                path.write_text(f'{{"value": {constant}}}', encoding="utf-8")
                with self.assertRaises(DataFormatError):
                    load_json(path)


if __name__ == "__main__":
    unittest.main()
