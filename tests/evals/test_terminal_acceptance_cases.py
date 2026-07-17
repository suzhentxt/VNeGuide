from __future__ import annotations

import json
import unittest
from pathlib import Path

CASES_PATH = Path(__file__).with_name("terminal_acceptance_cases.json")
ALLOWED_PROCEDURES = {
    None,
    "birth_extract",
    "marriage_extract",
    "death_extract",
    "unsupported",
}


class TerminalAcceptanceCasesTest(unittest.TestCase):
    def test_cases_are_well_formed_and_cover_required_acceptance_flows(self) -> None:
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        ids = [case["id"] for case in cases]
        procedures = {case["expected_procedure_type"] for case in cases}

        self.assertEqual(len(cases), 4)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(procedures <= ALLOWED_PROCEDURES)
        self.assertTrue(all(case["messages"] for case in cases))
        self.assertTrue(all(case["must_not_claim_acceptance"] for case in cases))
        self.assertIn("birth_extract", procedures)
        self.assertIn("death_extract", procedures)
        self.assertIn("unsupported", procedures)
        self.assertIn(None, procedures)


if __name__ == "__main__":
    unittest.main()
