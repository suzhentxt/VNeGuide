"""Domain models backed by the reviewed VNeGuide data package."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias

from .enums import (
    FieldType,
    IssueSeverity,
    PackStatus,
    ProcedureCode,
    RuleInputOrigin,
    SourceStatus,
    ValidationStatus,
)

JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = (
    JSONScalar
    | list["JSONValue"]
    | tuple["JSONValue", ...]
    | Mapping[str, "JSONValue"]
)


def freeze_json(value: JSONValue) -> JSONValue:
    """Return an immutable snapshot of JSON-compatible data."""

    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        return MappingProxyType({key: freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_json(item) for item in value)
    return value


def freeze_mapping(value: Mapping[str, JSONValue]) -> Mapping[str, JSONValue]:
    return MappingProxyType({key: freeze_json(item) for key, item in value.items()})


def _require_text(value: str, name: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be empty")


def _require_source_ids(source_ids: tuple[str, ...], owner: str) -> None:
    if not source_ids:
        raise ValueError(f"{owner} must reference at least one source_id")
    if any(not source_id.strip() for source_id in source_ids):
        raise ValueError(f"{owner} contains an empty source_id")


@dataclass(frozen=True, slots=True)
class FormDefinition:
    form_id: str
    name: str
    channel: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.form_id, "form_id")
        _require_text(self.name, "form name")
        _require_text(self.channel, "form channel")
        _require_source_ids(self.source_ids, self.form_id)


@dataclass(frozen=True, slots=True)
class ChecklistItem:
    item_id: str
    name: str
    requirement: str
    condition: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.item_id, "item_id")
        _require_text(self.name, "checklist item name")
        _require_text(self.requirement, "checklist requirement")
        _require_source_ids(self.source_ids, self.item_id)


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    procedure_code: ProcedureCode
    field_id: str
    label: str
    field_type: FieldType
    requirement: str
    source_ids: tuple[str, ...]
    values: tuple[JSONScalar, ...] = ()
    pattern: str | None = None
    minimum: int | float | None = None

    def __post_init__(self) -> None:
        _require_text(self.field_id, "field_id")
        _require_text(self.label, "field label")
        _require_text(self.requirement, "field requirement")
        _require_source_ids(self.source_ids, self.field_id)
        if self.field_type is FieldType.ENUM and not self.values:
            raise ValueError(f"enum field {self.field_id} must define values")


@dataclass(frozen=True, slots=True)
class ValidationRuleDefinition:
    procedure_code: ProcedureCode
    rule_id: str
    applies_to: ProcedureCode
    condition: str
    severity: IssueSeverity
    message: str
    suggestion: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.rule_id, "rule_id")
        _require_text(self.condition, "rule condition")
        _require_text(self.message, "rule message")
        _require_source_ids(self.source_ids, self.rule_id)
        if self.procedure_code is not self.applies_to:
            raise ValueError(
                f"rule {self.rule_id} applies to {self.applies_to}, "
                f"not {self.procedure_code}"
            )


@dataclass(frozen=True, slots=True)
class RuleContextInput:
    procedure_code: ProcedureCode
    input_id: str
    label: str
    field_type: FieldType
    origin: RuleInputOrigin
    source_ids: tuple[str, ...]
    values: tuple[JSONScalar, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.input_id, "rule context input_id")
        _require_text(self.label, "rule context label")
        _require_source_ids(self.source_ids, self.input_id)
        if self.field_type is FieldType.ENUM and not self.values:
            raise ValueError(f"enum rule input {self.input_id} must define values")


@dataclass(frozen=True, slots=True)
class GuidanceStep:
    step: int
    text: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.step < 1:
            raise ValueError("guidance step must be positive")
        _require_text(self.text, "guidance text")
        _require_source_ids(self.source_ids, f"guidance step {self.step}")


@dataclass(frozen=True, slots=True)
class Approval:
    owner: str
    reviewers: tuple[str, ...]
    approved_at: str

    def __post_init__(self) -> None:
        _require_text(self.owner, "approval owner")
        _require_text(self.approved_at, "approved_at")


@dataclass(frozen=True, slots=True)
class ProcedurePack:
    pack_id: str
    procedure_code: ProcedureCode
    procedure_name: str
    jurisdiction: str
    version: str
    status: PackStatus
    effective_from: str | None
    verified_at: str
    next_review_at: str
    scope: Mapping[str, JSONValue]
    routing: Mapping[str, JSONValue]
    service_info: Mapping[str, JSONValue]
    forms: tuple[FormDefinition, ...]
    checklist: tuple[ChecklistItem, ...]
    fields: tuple[FieldDefinition, ...]
    validation_rules: tuple[ValidationRuleDefinition, ...]
    guidance_steps: tuple[GuidanceStep, ...]
    source_ids: tuple[str, ...]
    approval: Approval

    def __post_init__(self) -> None:
        _require_text(self.pack_id, "pack_id")
        _require_text(self.procedure_name, "procedure_name")
        _require_text(self.version, "version")
        _require_source_ids(self.source_ids, self.pack_id)
        object.__setattr__(self, "scope", freeze_mapping(self.scope))
        object.__setattr__(self, "routing", freeze_mapping(self.routing))
        object.__setattr__(self, "service_info", freeze_mapping(self.service_info))


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: str
    title: str
    procedure_code: str | None
    publisher: str
    jurisdiction: str
    effective_from: str | None
    verified_at: str
    authority_tier: str
    status: SourceStatus
    url: str
    local_file: str | None
    used_for: tuple[str, ...]
    notes: str

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        _require_text(self.title, "source title")
        _require_text(self.publisher, "source publisher")
        _require_text(self.verified_at, "source verified_at")


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    rule_id: str
    severity: IssueSeverity
    message: str
    source_ids: tuple[str, ...]
    field_id: str | None = None
    suggestion: str = ""

    def __post_init__(self) -> None:
        _require_text(self.rule_id, "rule_id")
        _require_text(self.message, "issue message")
        _require_source_ids(self.source_ids, self.rule_id)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    procedure_code: ProcedureCode
    status: ValidationStatus
    issues: tuple[ValidationIssue, ...]
    passed_checks: tuple[str, ...]
    source_ids: tuple[str, ...]
    readiness_score: int | None = None

    def __post_init__(self) -> None:
        if self.readiness_score is not None and not 0 <= self.readiness_score <= 100:
            raise ValueError("readiness_score must be between 0 and 100")
        _require_source_ids(self.source_ids, f"validation result {self.procedure_code}")
