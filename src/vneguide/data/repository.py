"""Validated, read-only access to the reviewed VNeGuide data package."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from vneguide.domain import (
    Approval,
    ChecklistItem,
    FieldDefinition,
    FieldType,
    FormDefinition,
    GuidanceStep,
    IssueSeverity,
    PackStatus,
    ProcedureCode,
    ProcedurePack,
    RuleContextInput,
    RuleInputOrigin,
    SourceRecord,
    SourceStatus,
    ValidationRuleDefinition,
)

from .errors import DataIntegrityError, DataPackageError
from .loader import DataPackagePaths, load_json_array, load_json_object
from .schema_validator import assert_json_schema


def _strings(value: object, context: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise DataIntegrityError(f"{context} must be an array of strings")
    return tuple(value)


def _text(raw: Mapping[str, Any], name: str, context: str) -> str:
    value = raw.get(name)
    if not isinstance(value, str):
        raise DataIntegrityError(f"{context}.{name} must be a string")
    return value


def _optional_text(raw: Mapping[str, Any], name: str, context: str) -> str | None:
    value = raw.get(name)
    if value is not None and not isinstance(value, str):
        raise DataIntegrityError(f"{context}.{name} must be a string or null")
    return value


def _integer(raw: Mapping[str, Any], name: str, context: str) -> int:
    value = raw.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise DataIntegrityError(f"{context}.{name} must be an integer")
    return value


def _mapping(raw: Mapping[str, Any], name: str, context: str) -> dict[str, Any]:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise DataIntegrityError(f"{context}.{name} must be an object")
    return dict(value)


def _records(raw: Mapping[str, Any], name: str, context: str) -> list[dict[str, Any]]:
    value = raw.get(name)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise DataIntegrityError(f"{context}.{name} must be an array of objects")
    return value


def _parse_field(raw: Mapping[str, Any], procedure_code: ProcedureCode) -> FieldDefinition:
    context = f"field[{raw.get('field_id', '?')}]"
    raw_values = raw.get("values", [])
    if not isinstance(raw_values, list):
        raise DataIntegrityError(f"{context}.values must be an array")
    minimum = raw.get("minimum")
    if minimum is not None and (not isinstance(minimum, (int, float)) or isinstance(minimum, bool)):
        raise DataIntegrityError(f"{context}.minimum must be a number")
    pattern = raw.get("pattern")
    if pattern is not None and not isinstance(pattern, str):
        raise DataIntegrityError(f"{context}.pattern must be a string")
    return FieldDefinition(
        procedure_code=procedure_code,
        field_id=_text(raw, "field_id", context),
        label=_text(raw, "label", context),
        field_type=FieldType(_text(raw, "type", context)),
        requirement=_text(raw, "requirement", context),
        source_ids=_strings(raw.get("source_ids"), f"{context}.source_ids"),
        values=tuple(raw_values),
        pattern=pattern,
        minimum=minimum,
    )


def _parse_rule(raw: Mapping[str, Any], procedure_code: ProcedureCode) -> ValidationRuleDefinition:
    context = f"rule[{raw.get('rule_id', '?')}]"
    return ValidationRuleDefinition(
        procedure_code=procedure_code,
        rule_id=_text(raw, "rule_id", context),
        applies_to=ProcedureCode(_text(raw, "applies_to", context)),
        condition=_text(raw, "condition", context),
        severity=IssueSeverity(_text(raw, "severity", context)),
        message=_text(raw, "message", context),
        suggestion=_text(raw, "suggestion", context),
        source_ids=_strings(raw.get("source_ids"), f"{context}.source_ids"),
    )


def _parse_rule_input(raw: Mapping[str, Any]) -> RuleContextInput:
    context = f"rule_context[{raw.get('input_id', '?')}]"
    raw_values = raw.get("values", [])
    if not isinstance(raw_values, list):
        raise DataIntegrityError(f"{context}.values must be an array")
    return RuleContextInput(
        procedure_code=ProcedureCode(_text(raw, "procedure_code", context)),
        input_id=_text(raw, "input_id", context),
        label=_text(raw, "label", context),
        field_type=FieldType(_text(raw, "type", context)),
        origin=RuleInputOrigin(_text(raw, "origin", context)),
        source_ids=_strings(raw.get("source_ids"), f"{context}.source_ids"),
        values=tuple(raw_values),
    )


def _parse_pack(raw: Mapping[str, Any]) -> ProcedurePack:
    context = f"pack[{raw.get('pack_id', '?')}]"
    procedure_code = ProcedureCode(_text(raw, "procedure_code", context))

    forms = tuple(
        FormDefinition(
            form_id=_text(item, "form_id", context),
            name=_text(item, "name", context),
            channel=_text(item, "channel", context),
            source_ids=_strings(item.get("source_ids"), f"{context}.forms.source_ids"),
        )
        for item in _records(raw, "forms", context)
    )
    checklist = tuple(
        ChecklistItem(
            item_id=_text(item, "item_id", context),
            name=_text(item, "name", context),
            requirement=_text(item, "requirement", context),
            condition=_text(item, "condition", context),
            source_ids=_strings(item.get("source_ids"), f"{context}.checklist.source_ids"),
        )
        for item in _records(raw, "checklist", context)
    )
    fields = tuple(_parse_field(item, procedure_code) for item in _records(raw, "fields", context))
    rules = tuple(
        _parse_rule(item, procedure_code) for item in _records(raw, "validation_rules", context)
    )
    steps = tuple(
        GuidanceStep(
            step=_integer(item, "step", context),
            text=_text(item, "text", context),
            source_ids=_strings(item.get("source_ids"), f"{context}.guidance_steps.source_ids"),
        )
        for item in _records(raw, "guidance_steps", context)
    )

    approval_raw = _mapping(raw, "approval", context)
    approval = Approval(
        owner=_text(approval_raw, "owner", f"{context}.approval"),
        reviewers=_strings(approval_raw.get("reviewers"), f"{context}.approval.reviewers"),
        approved_at=_text(approval_raw, "approved_at", f"{context}.approval"),
    )

    return ProcedurePack(
        pack_id=_text(raw, "pack_id", context),
        procedure_code=procedure_code,
        procedure_name=_text(raw, "procedure_name", context),
        jurisdiction=_text(raw, "jurisdiction", context),
        version=_text(raw, "version", context),
        status=PackStatus(_text(raw, "status", context)),
        effective_from=_optional_text(raw, "effective_from", context),
        verified_at=_text(raw, "verified_at", context),
        next_review_at=_text(raw, "next_review_at", context),
        scope=_mapping(raw, "scope", context),
        routing=_mapping(raw, "routing", context),
        service_info=_mapping(raw, "service_info", context),
        forms=forms,
        checklist=checklist,
        fields=fields,
        validation_rules=rules,
        guidance_steps=steps,
        source_ids=_strings(raw.get("source_ids"), f"{context}.source_ids"),
        approval=approval,
    )


def _parse_source(raw: Mapping[str, Any]) -> SourceRecord:
    context = f"source[{raw.get('source_id', '?')}]"
    return SourceRecord(
        source_id=_text(raw, "source_id", context),
        title=_text(raw, "title", context),
        procedure_code=_optional_text(raw, "procedure_code", context),
        publisher=_text(raw, "publisher", context),
        jurisdiction=_text(raw, "jurisdiction", context),
        effective_from=_optional_text(raw, "effective_from", context),
        verified_at=_text(raw, "verified_at", context),
        authority_tier=_text(raw, "authority_tier", context),
        status=SourceStatus(_text(raw, "status", context)),
        url=_text(raw, "url", context),
        local_file=_optional_text(raw, "local_file", context),
        used_for=_strings(raw.get("used_for"), f"{context}.used_for"),
        notes=_text(raw, "notes", context),
    )


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


_CONDITION_KEYWORDS = frozenset(
    {
        "always",
        "and",
        "digits",
        "does",
        "empty",
        "false",
        "in",
        "is",
        "match",
        "not",
        "or",
        "present",
        "true",
    }
)


def _condition_identifiers(condition: str) -> set[str]:
    without_literals = re.sub(r"'[^']*'|\"[^\"]*\"", "", condition)
    return {
        identifier
        for identifier in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", without_literals)
        if identifier not in _CONDITION_KEYWORDS
    }


class ProcedureRepository:
    """Loads and audits all reviewed procedure data as immutable domain models."""

    def __init__(self, paths: DataPackagePaths | None = None) -> None:
        self.paths = paths or DataPackagePaths.discover()
        self._packs_by_code: dict[ProcedureCode, ProcedurePack] = {}
        self._packs_by_id: dict[str, ProcedurePack] = {}
        self._sources_by_id: dict[str, SourceRecord] = {}
        self._fields: tuple[FieldDefinition, ...] = ()
        self._rules: tuple[ValidationRuleDefinition, ...] = ()
        self._rule_inputs: tuple[RuleContextInput, ...] = ()
        self._load()

    @classmethod
    def discover(cls, start: str | Path | None = None) -> ProcedureRepository:
        return cls(DataPackagePaths.discover(start))

    def _load(self) -> None:
        pack_schema = load_json_object(self.paths.contracts / "procedure-pack.schema.json")
        raw_packs = [
            load_json_object(path)
            for path in sorted((self.paths.catalog / "procedure_packs").glob("*.json"))
        ]
        if not raw_packs:
            raise DataIntegrityError("no procedure packs found")
        for raw_pack in raw_packs:
            assert_json_schema(raw_pack, pack_schema)
            try:
                pack = _parse_pack(raw_pack)
            except (TypeError, ValueError) as exc:
                raise DataIntegrityError(f"invalid procedure pack: {exc}") from exc
            if pack.procedure_code in self._packs_by_code:
                raise DataIntegrityError(f"duplicate procedure code {pack.procedure_code}")
            if pack.pack_id in self._packs_by_id:
                raise DataIntegrityError(f"duplicate pack_id {pack.pack_id}")
            self._packs_by_code[pack.procedure_code] = pack
            self._packs_by_id[pack.pack_id] = pack

        for raw_source in load_json_array(self.paths.catalog / "source_register.json"):
            try:
                source = _parse_source(raw_source)
            except (TypeError, ValueError) as exc:
                raise DataIntegrityError(f"invalid source record: {exc}") from exc
            if source.source_id in self._sources_by_id:
                raise DataIntegrityError(f"duplicate source_id {source.source_id}")
            self._sources_by_id[source.source_id] = source

        try:
            self._fields = tuple(
                _parse_field(raw, ProcedureCode(_text(raw, "procedure_code", "field_catalog")))
                for raw in load_json_array(self.paths.catalog / "field_catalog.json")
            )
            self._rules = tuple(
                _parse_rule(raw, ProcedureCode(_text(raw, "procedure_code", "validation_rules")))
                for raw in load_json_array(self.paths.catalog / "validation_rules.json")
            )
            raw_rule_inputs = load_json_array(self.paths.catalog / "rule_context_catalog.json")
            rule_input_schema = load_json_object(self.paths.contracts / "rule-context.schema.json")
            assert_json_schema(raw_rule_inputs, rule_input_schema)
            self._rule_inputs = tuple(_parse_rule_input(raw) for raw in raw_rule_inputs)
        except (TypeError, ValueError) as exc:
            raise DataIntegrityError(f"invalid catalog record: {exc}") from exc

        problems = self.audit()
        if problems:
            raise DataIntegrityError("; ".join(problems))

    def audit(self) -> tuple[str, ...]:
        problems: list[str] = []

        missing_codes = set(ProcedureCode) - set(self._packs_by_code)
        extra_codes = set(self._packs_by_code) - set(ProcedureCode)
        if missing_codes:
            problems.append(f"missing approved procedure packs: {sorted(missing_codes)}")
        if extra_codes:
            problems.append(f"unexpected procedure packs: {sorted(extra_codes)}")

        for pack in self._packs_by_code.values():
            if pack.status is not PackStatus.APPROVED:
                problems.append(f"runtime pack {pack.pack_id} is not approved")
            problems.extend(self._audit_pack(pack))

        field_keys = [(field.procedure_code, field.field_id) for field in self._fields]
        rule_keys = [(rule.procedure_code, rule.rule_id) for rule in self._rules]
        duplicate_fields = _duplicates(f"{code}:{field_id}" for code, field_id in field_keys)
        duplicate_rules = _duplicates(f"{code}:{rule_id}" for code, rule_id in rule_keys)
        rule_input_keys = [(item.procedure_code, item.input_id) for item in self._rule_inputs]
        duplicate_rule_inputs = _duplicates(
            f"{code}:{input_id}" for code, input_id in rule_input_keys
        )
        if duplicate_fields:
            problems.append(f"duplicate catalog fields: {sorted(duplicate_fields)}")
        if duplicate_rules:
            problems.append(f"duplicate catalog rules: {sorted(duplicate_rules)}")
        if duplicate_rule_inputs:
            problems.append(f"duplicate rule context inputs: {sorted(duplicate_rule_inputs)}")

        pack_fields_by_key = {
            (pack.procedure_code, field.field_id): field
            for pack in self._packs_by_code.values()
            for field in pack.fields
        }
        pack_rules_by_key = {
            (pack.procedure_code, rule.rule_id): rule
            for pack in self._packs_by_code.values()
            for rule in pack.validation_rules
        }
        catalog_fields_by_key = {
            (field.procedure_code, field.field_id): field for field in self._fields
        }
        catalog_rules_by_key = {(rule.procedure_code, rule.rule_id): rule for rule in self._rules}
        if catalog_fields_by_key.keys() != pack_fields_by_key.keys():
            problems.append("field_catalog does not mirror procedure pack fields")
        else:
            for key, catalog_field in catalog_fields_by_key.items():
                if catalog_field != pack_fields_by_key[key]:
                    problems.append(f"field_catalog content differs for {key[0]}:{key[1]}")
        if catalog_rules_by_key.keys() != pack_rules_by_key.keys():
            problems.append("validation_rules does not mirror procedure pack rules")
        else:
            for key, catalog_rule in catalog_rules_by_key.items():
                if catalog_rule != pack_rules_by_key[key]:
                    problems.append(f"validation_rules content differs for {key[0]}:{key[1]}")

        for source in self._sources_by_id.values():
            if source.local_file:
                local_path = (self.paths.root / source.local_file).resolve()
                if not local_path.is_relative_to(self.paths.root):
                    problems.append(
                        f"source {source.source_id} local_file escapes data root: "
                        f"{source.local_file}"
                    )
                    continue
                if not local_path.is_file():
                    problems.append(
                        f"source {source.source_id} local_file does not exist: {source.local_file}"
                    )

        for field in self._fields:
            problems.extend(
                self._source_problems(field.field_id, field.source_ids, field.procedure_code)
            )
        for rule in self._rules:
            problems.extend(
                self._source_problems(rule.rule_id, rule.source_ids, rule.procedure_code)
            )
        for item in self._rule_inputs:
            problems.extend(
                self._source_problems(item.input_id, item.source_ids, item.procedure_code)
            )
        problems.extend(self.verify_checksums())
        return tuple(problems)

    def _audit_pack(self, pack: ProcedurePack) -> list[str]:
        problems: list[str] = []
        identifiers = {
            "form": [item.form_id for item in pack.forms],
            "checklist": [item.item_id for item in pack.checklist],
            "field": [item.field_id for item in pack.fields],
            "rule": [item.rule_id for item in pack.validation_rules],
        }
        for kind, values in identifiers.items():
            duplicate_ids = _duplicates(values)
            if duplicate_ids:
                problems.append(
                    f"pack {pack.pack_id} has duplicate {kind} ids: {sorted(duplicate_ids)}"
                )

        step_numbers = [item.step for item in pack.guidance_steps]
        expected_steps = list(range(1, len(step_numbers) + 1))
        if step_numbers != expected_steps:
            problems.append(
                f"pack {pack.pack_id} guidance steps must be ordered and contiguous from 1"
            )

        declared_rule_inputs = {item.field_id for item in pack.fields}
        declared_rule_inputs.update(
            item.input_id
            for item in self._rule_inputs
            if item.procedure_code is pack.procedure_code
        )
        for rule in pack.validation_rules:
            missing_inputs = _condition_identifiers(rule.condition) - declared_rule_inputs
            if missing_inputs:
                problems.append(
                    f"rule {rule.rule_id} uses undeclared inputs: {sorted(missing_inputs)}"
                )

        sourced_items: list[tuple[str, tuple[str, ...]]] = [(pack.pack_id, pack.source_ids)]
        sourced_items.extend((item.form_id, item.source_ids) for item in pack.forms)
        sourced_items.extend((item.item_id, item.source_ids) for item in pack.checklist)
        sourced_items.extend((item.field_id, item.source_ids) for item in pack.fields)
        sourced_items.extend((item.rule_id, item.source_ids) for item in pack.validation_rules)
        sourced_items.extend(
            (f"{pack.pack_id}:step:{item.step}", item.source_ids) for item in pack.guidance_steps
        )
        for owner, source_ids in sourced_items:
            problems.extend(self._source_problems(owner, source_ids, pack.procedure_code))
        return problems

    def _source_problems(
        self,
        owner: str,
        source_ids: tuple[str, ...],
        procedure_code: ProcedureCode,
    ) -> list[str]:
        problems: list[str] = []
        for source_id in source_ids:
            source = self._sources_by_id.get(source_id)
            if source is None:
                problems.append(f"{owner} references unknown source_id {source_id}")
                continue
            if source.status is not SourceStatus.APPROVED:
                problems.append(
                    f"{owner} references non-approved source_id {source_id}: {source.status}"
                )
            if source.procedure_code not in (None, procedure_code.value):
                problems.append(
                    f"{owner} references source_id {source_id} for "
                    f"procedure {source.procedure_code}"
                )
        return problems

    def verify_checksums(self) -> tuple[str, ...]:
        """Verify QA hashes using LF-normalized bytes for text artifacts."""

        problems: list[str] = []
        roots = (
            self.paths.catalog,
            self.paths.catalog / "procedure_packs",
            self.paths.contracts,
            self.paths.evaluation,
        )
        for checksum_path in sorted(self.paths.qa.glob("*.sha256")):
            parts = checksum_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
            if len(parts) != 2:
                problems.append(f"invalid checksum file {checksum_path.name}")
                continue
            expected, filename = parts
            candidates = [root / filename for root in roots if (root / filename).is_file()]
            if len(candidates) != 1:
                problems.append(
                    f"checksum {checksum_path.name} resolves to {len(candidates)} artifacts"
                )
                continue
            actual = self._artifact_sha256(candidates[0])
            if actual != expected.lower():
                problems.append(
                    f"checksum mismatch for {filename}: expected {expected.lower()}, got {actual}"
                )
        return tuple(problems)

    @staticmethod
    def _artifact_sha256(path: Path) -> str:
        content = path.read_bytes()
        if path.suffix.lower() in {".json", ".jsonl", ".md", ".txt"}:
            text = content.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
            content = text.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def list_procedures(self) -> tuple[ProcedurePack, ...]:
        return tuple(sorted(self._packs_by_code.values(), key=lambda pack: pack.procedure_code))

    def get_by_code(self, procedure_code: ProcedureCode | str) -> ProcedurePack:
        try:
            code = ProcedureCode(procedure_code)
            return self._packs_by_code[code]
        except (ValueError, KeyError) as exc:
            raise DataPackageError(f"unsupported procedure code: {procedure_code}") from exc

    def get_by_pack_id(self, pack_id: str) -> ProcedurePack:
        try:
            return self._packs_by_id[pack_id]
        except KeyError as exc:
            raise DataPackageError(f"unknown pack_id: {pack_id}") from exc

    def get_source(self, source_id: str) -> SourceRecord:
        try:
            return self._sources_by_id[source_id]
        except KeyError as exc:
            raise DataPackageError(f"unknown source_id: {source_id}") from exc

    def resolve_sources(self, source_ids: Iterable[str]) -> tuple[SourceRecord, ...]:
        return tuple(self.get_source(source_id) for source_id in source_ids)

    def fields_for(self, procedure_code: ProcedureCode | str) -> tuple[FieldDefinition, ...]:
        code = self.get_by_code(procedure_code).procedure_code
        return tuple(field for field in self._fields if field.procedure_code is code)

    def rules_for(
        self, procedure_code: ProcedureCode | str
    ) -> tuple[ValidationRuleDefinition, ...]:
        code = self.get_by_code(procedure_code).procedure_code
        return tuple(rule for rule in self._rules if rule.procedure_code is code)

    def rule_inputs_for(self, procedure_code: ProcedureCode | str) -> tuple[RuleContextInput, ...]:
        code = self.get_by_code(procedure_code).procedure_code
        return tuple(item for item in self._rule_inputs if item.procedure_code is code)

    def local_source_path(self, source_id: str) -> Path | None:
        source = self.get_source(source_id)
        if source.local_file is None:
            return None
        return (self.paths.root / source.local_file).resolve()

    def validate_result_document(self, document: Mapping[str, Any]) -> None:
        schema = load_json_object(self.paths.contracts / "validation-result.schema.json")
        assert_json_schema(document, schema)
        try:
            code = ProcedureCode(document["procedure_code"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DataIntegrityError("validation result has unsupported procedure_code") from exc

        known_rules = {rule.rule_id for rule in self.rules_for(code)}
        known_fields = {field.field_id for field in self.fields_for(code)}
        for rule_id in document.get("passed_checks", []):
            if rule_id not in known_rules:
                raise DataIntegrityError(f"validation result references unknown rule_id {rule_id}")
        for issue in document.get("issues", []):
            rule_id = issue.get("rule_id")
            if rule_id not in known_rules:
                raise DataIntegrityError(f"validation result references unknown rule_id {rule_id}")
            field_id = issue.get("field_id")
            if field_id is not None and field_id not in known_fields:
                raise DataIntegrityError(
                    f"validation result references unknown field_id {field_id}"
                )
            self._assert_approved_result_sources(issue.get("source_ids", []), code)
        self._assert_approved_result_sources(document.get("source_ids", []), code)

    def _assert_approved_result_sources(
        self, source_ids: Iterable[str], procedure_code: ProcedureCode
    ) -> None:
        source_ids = tuple(source_ids)
        if not source_ids:
            raise DataIntegrityError("validation result must reference at least one source_id")
        problems = self._source_problems("validation result", source_ids, procedure_code)
        if problems:
            raise DataIntegrityError("; ".join(problems))
