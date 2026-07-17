"""Contract and integrity tests against the checked-in data package."""

import unittest
from pathlib import Path

from vneguide.data import (
    DataIntegrityError,
    DataPackageError,
    DataPackagePaths,
    ProcedureRepository,
    SchemaValidationError,
)
from vneguide.domain import PackStatus, ProcedureCode, SourceStatus

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class ProcedureRepositoryTests(unittest.TestCase):
    paths: DataPackagePaths
    repository: ProcedureRepository

    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = DataPackagePaths.from_root(REPOSITORY_ROOT / "data")
        cls.repository = ProcedureRepository(cls.paths)

    def test_loads_exactly_the_approved_mvp_scope(self) -> None:
        packs = self.repository.list_procedures()
        self.assertEqual({pack.procedure_code for pack in packs}, set(ProcedureCode))
        self.assertTrue(all(pack.status is PackStatus.APPROVED for pack in packs))

    def test_global_field_and_rule_catalogs_mirror_each_pack(self) -> None:
        for pack in self.repository.list_procedures():
            self.assertEqual(self.repository.fields_for(pack.procedure_code), pack.fields)
            self.assertEqual(self.repository.rules_for(pack.procedure_code), pack.validation_rules)

    def test_full_data_package_audit_passes(self) -> None:
        self.assertEqual(self.repository.audit(), ())
        self.assertEqual(self.repository.verify_checksums(), ())

    def test_non_form_rule_inputs_are_explicitly_cataloged(self) -> None:
        expected = {
            ProcedureCode.BIRTH_CERTIFICATE_COPY: {
                "requested_variant",
                "intent",
                "authorization_document_missing",
                "certified_copies_missing",
                "uploaded_document_quality",
                "foreign_issued_document_present",
            },
            ProcedureCode.HOUSING_CONDITION_CONFIRMATION: {"mau_02_missing"},
            ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION: {
                "ct01_missing",
                "document_marked_not_notarized",
                "newly_naturalized_or_restored_citizenship",
            },
        }
        for code, expected_ids in expected.items():
            self.assertEqual(
                {item.input_id for item in self.repository.rule_inputs_for(code)},
                expected_ids,
            )

    def test_every_referenced_source_resolves(self) -> None:
        for pack in self.repository.list_procedures():
            sources = self.repository.resolve_sources(pack.source_ids)
            self.assertEqual({source.source_id for source in sources}, set(pack.source_ids))
            self.assertTrue(all(source.status is SourceStatus.APPROVED for source in sources))

    def test_registered_local_sources_exist_inside_data_package(self) -> None:
        for pack in self.repository.list_procedures():
            for source_id in pack.source_ids:
                local_path = self.repository.local_source_path(source_id)
                if local_path is not None:
                    self.assertTrue(local_path.is_file())
                    self.assertTrue(local_path.is_relative_to(self.paths.root))

    def test_unknown_procedure_is_rejected(self) -> None:
        with self.assertRaisesRegex(DataPackageError, "unsupported procedure"):
            self.repository.get_by_code("marriage_extract")

    def test_validation_result_contract_accepts_gold_shape(self) -> None:
        self.repository.validate_result_document(
            {
                "procedure_code": "2.000635",
                "status": "ready_to_submit",
                "readiness_score": 100,
                "issues": [],
                "passed_checks": ["BIRTH-ID-001"],
                "source_ids": ["SRC-DVC-2000635"],
            }
        )

    def test_validation_result_contract_rejects_unknown_status(self) -> None:
        with self.assertRaises(SchemaValidationError):
            self.repository.validate_result_document(
                {
                    "procedure_code": "2.000635",
                    "status": "accepted_by_authority",
                    "issues": [],
                    "passed_checks": [],
                    "source_ids": ["SRC-DVC-2000635"],
                }
            )

    def test_validation_result_rejects_unknown_procedure_rule_and_source(self) -> None:
        base = {
            "procedure_code": "2.000635",
            "status": "needs_correction",
            "issues": [],
            "passed_checks": [],
            "source_ids": ["SRC-DVC-2000635"],
        }
        with self.assertRaisesRegex(SchemaValidationError, "procedure_code"):
            self.repository.validate_result_document({**base, "procedure_code": "marriage_extract"})
        with self.assertRaisesRegex(DataIntegrityError, "unknown rule_id"):
            self.repository.validate_result_document({**base, "passed_checks": ["UNKNOWN-RULE"]})
        with self.assertRaisesRegex(DataIntegrityError, "unknown source_id"):
            self.repository.validate_result_document({**base, "source_ids": ["UNKNOWN-SOURCE"]})
        with self.assertRaisesRegex(DataIntegrityError, "at least one source_id"):
            self.repository.validate_result_document({**base, "source_ids": []})
        with self.assertRaisesRegex(DataIntegrityError, "unknown field_id"):
            self.repository.validate_result_document(
                {
                    **base,
                    "issues": [
                        {
                            "rule_id": "BIRTH-ID-001",
                            "field_id": "unknown_field",
                            "severity": "error",
                            "message": "invalid",
                            "source_ids": ["SRC-DVC-2000635"],
                        }
                    ],
                }
            )
        with self.assertRaisesRegex(SchemaValidationError, "unexpected property"):
            self.repository.validate_result_document({**base, "authority_accepted": True})


if __name__ == "__main__":
    unittest.main()
