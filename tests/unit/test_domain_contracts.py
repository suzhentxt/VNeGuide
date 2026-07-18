"""Unit tests for the contracts owned by the Domain & Data Lead."""

import unittest
from typing import Any, cast

from vneguide.domain import (
    CaseDraft,
    ConversationState,
    ExtractionResult,
    JSONValue,
    ProcedureCode,
    TurnRequest,
    ValidationResult,
    ValidationStatus,
)


class ProcedureCodeTests(unittest.TestCase):
    def test_current_scope_has_exactly_three_codes(self) -> None:
        self.assertEqual(
            {code.value for code in ProcedureCode},
            {"2.000635", "1.013314", "1.004194"},
        )

    def test_removed_extract_variants_are_not_supported(self) -> None:
        with self.assertRaises(ValueError):
            ProcedureCode("marriage_extract")
        with self.assertRaises(ValueError):
            ProcedureCode("death_extract")


class DraftContractTests(unittest.TestCase):
    def test_rejects_negative_revision(self) -> None:
        with self.assertRaisesRegex(ValueError, "revision"):
            CaseDraft(revision=-1)

    def test_confirmed_and_dirty_fields_must_have_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "confirmed fields"):
            CaseDraft(confirmed_fields=frozenset({"missing"}))
        with self.assertRaisesRegex(ValueError, "dirty fields"):
            CaseDraft(dirty_fields=frozenset({"missing"}))

    def test_dirty_fields_must_also_be_confirmed(self) -> None:
        with self.assertRaisesRegex(ValueError, "not confirmed"):
            CaseDraft(
                values={"field": "value"},
                dirty_fields=frozenset({"field"}),
            )

    def test_valid_draft_supports_generic_procedure_fields(self) -> None:
        mutable_values: dict[str, JSONValue] = {
            "allocated_area_m2": 30,
            "details": {"zone": "inner_city"},
        }
        draft = CaseDraft(
            procedure_code=ProcedureCode.HOUSING_CONDITION_CONFIRMATION,
            values=mutable_values,
            confirmed_fields=frozenset({"allocated_area_m2"}),
            revision=1,
            pack_version="2.0.0",
        )
        mutable_values["allocated_area_m2"] = 1
        self.assertEqual(draft.values["allocated_area_m2"], 30)
        with self.assertRaises(TypeError):
            draft.values["allocated_area_m2"] = 1  # type: ignore[index]
        with self.assertRaises(TypeError):
            cast(Any, draft.values["details"])["zone"] = "suburban"


class TurnContractTests(unittest.TestCase):
    def test_request_rejects_blank_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "message"):
            TurnRequest("   ")

    def test_extraction_confidence_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "confidence"):
            ExtractionResult(None, confidence=1.01)

    def test_conversation_counters_cannot_be_negative(self) -> None:
        with self.assertRaisesRegex(ValueError, "turn_number"):
            ConversationState(turn_number=-1)
        with self.assertRaisesRegex(ValueError, "clarification"):
            ConversationState(clarification_attempts={"field": -1})

    def test_asked_question_ids_must_be_non_empty_and_unique(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty"):
            ConversationState(asked_question_ids=("",))
        with self.assertRaisesRegex(ValueError, "unique"):
            ConversationState(asked_question_ids=("procedure:field", "procedure:field"))


class ValidationResultTests(unittest.TestCase):
    def test_readiness_score_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "readiness_score"):
            ValidationResult(
                procedure_code=ProcedureCode.BIRTH_CERTIFICATE_COPY,
                status=ValidationStatus.NEEDS_CORRECTION,
                issues=(),
                passed_checks=(),
                source_ids=("SRC-DVC-2000635",),
                readiness_score=101,
            )


if __name__ == "__main__":
    unittest.main()
