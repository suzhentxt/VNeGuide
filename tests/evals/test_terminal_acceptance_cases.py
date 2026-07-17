from __future__ import annotations

import json
import unittest
from pathlib import Path

CASES_PATH = Path(__file__).with_name("terminal_acceptance_cases.json")
APPROVED_PROCEDURE_CODES = {"2.000635", "1.013314", "1.004194"}
ALLOWED_FINAL_STATES = {None, "out_of_scope"}


class TerminalAcceptanceCasesTest(unittest.TestCase):
    def test_cases_are_well_formed_and_cover_required_acceptance_flows(self) -> None:
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        ids = [case["id"] for case in cases]
        procedure_codes = {case["expected_procedure_code"] for case in cases}
        final_states = {case["expected_final_state"] for case in cases}

        self.assertEqual(len(cases), 4)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(procedure_codes - {None}, APPROVED_PROCEDURE_CODES)
        self.assertTrue(final_states <= ALLOWED_FINAL_STATES)
        self.assertTrue(all(case["messages"] for case in cases))
        self.assertTrue(all(case["must_not_claim_acceptance"] for case in cases))
        self.assertIn(None, procedure_codes)
        self.assertIn("out_of_scope", final_states)


if __name__ == "__main__":
    unittest.main()
