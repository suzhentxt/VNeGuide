"""Contract and integrity tests against the checked-in data package."""

import json
import operator
import shutil
import unittest
from collections.abc import MutableMapping
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

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

    def test_all_packs_expose_traceable_service_info_at_version_2_1(self) -> None:
        expected_keys = {
            "authority",
            "channels",
            "processing_time_display",
            "fee",
            "result",
        }
        for pack in self.repository.list_procedures():
            self.assertEqual(pack.version, "2.1.0")
            self.assertEqual(set(pack.service_info), expected_keys)
            self.assertEqual(set(pack.service_info_sources), expected_keys)
            with self.assertRaises(TypeError):
                operator.setitem(
                    cast(MutableMapping[str, tuple[str, ...]], pack.service_info_sources),
                    "authority",
                    ("UNKNOWN",),
                )
            for source_ids in pack.service_info_sources.values():
                self.assertTrue(source_ids)
                self.assertTrue(set(source_ids).issubset(pack.source_ids))
                for source_id in source_ids:
                    source = self.repository.get_source(source_id)
                    self.assertIs(source.status, SourceStatus.APPROVED)
                    self.assertIn(
                        source.procedure_code,
                        (None, pack.procedure_code.value),
                    )

    def test_registration_mode_help_is_reviewed_complete_and_immutable(self) -> None:
        field = next(
            item
            for item in self.repository.fields_for(ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION)
            if item.field_id == "registration_mode"
        )
        self.assertIsNotNone(field.help_text)
        self.assertEqual(set(field.choice_help), set(field.values))
        self.assertIn("CT01", field.choice_help["by_list"])
        self.assertIn("kiểm tra chính thức", field.choice_help["by_list"])
        self.assertIn("nhà ở công vụ", field.choice_help["armed_forces"])
        self.assertIn("kiểm tra chính thức", field.choice_help["armed_forces"])
        with self.assertRaises(TypeError):
            operator.setitem(
                cast(MutableMapping[str, str], field.choice_help),
                "by_list",
                "changed",
            )
        with self.assertRaisesRegex(ValueError, "unknown choices"):
            replace(field, choice_help={"unsupported": "Không hợp lệ"})
        with self.assertRaisesRegex(ValueError, "non-empty strings"):
            replace(field, choice_help={"by_list": ""})

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

    def test_service_info_source_must_match_its_procedure(self) -> None:
        with TemporaryDirectory() as directory:
            data_root = Path(directory) / "data"
            shutil.copytree(self.paths.root, data_root)
            pack_path = data_root / "catalog/procedure_packs/birth_certificate_copy.json"
            raw = json.loads(pack_path.read_text(encoding="utf-8"))
            raw["service_info_sources"]["authority"] = ["SRC-DVC-1013314"]
            pack_path.write_text(
                json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DataIntegrityError,
                "service_info:authority references source_id SRC-DVC-1013314 "
                "for procedure 1.013314",
            ):
                ProcedureRepository(DataPackagePaths.from_root(data_root))

    def test_service_info_sources_must_cover_exact_service_info_keys(self) -> None:
        with TemporaryDirectory() as directory:
            data_root = Path(directory) / "data"
            shutil.copytree(self.paths.root, data_root)
            pack_path = data_root / "catalog/procedure_packs/birth_certificate_copy.json"
            raw = json.loads(pack_path.read_text(encoding="utf-8"))
            del raw["service_info_sources"]["result"]
            pack_path.write_text(
                json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                SchemaValidationError, "missing required property 'result'"
            ):
                ProcedureRepository(DataPackagePaths.from_root(data_root))

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
