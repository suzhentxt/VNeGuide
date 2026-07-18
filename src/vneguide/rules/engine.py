"""Deterministic validation over reviewed procedure rules."""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Mapping
from datetime import date
from typing import TypeAlias

from vneguide.data import ProcedureRepository
from vneguide.domain import (
    FieldDefinition,
    FieldType,
    IssueSeverity,
    JSONValue,
    ProcedureCode,
    RuleInputOrigin,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)

RulePredicate: TypeAlias = Callable[[Mapping[str, JSONValue]], bool]
_TEXT_CONTEXT_ORIGINS = frozenset(
    {RuleInputOrigin.INTENT_EXTRACTION, RuleInputOrigin.USER_DECLARATION}
)
_ADAPTER_CONTEXT_ORIGINS = frozenset({RuleInputOrigin.DOCUMENT_CHECK, RuleInputOrigin.DERIVED})


def _present(values: Mapping[str, JSONValue], key: str) -> bool:
    return key in values and values[key] not in (None, "")


def _text(values: Mapping[str, JSONValue], key: str) -> str | None:
    value = values.get(key)
    return value if isinstance(value, str) else None


def _number(values: Mapping[str, JSONValue], key: str) -> float | None:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _is_bad_personal_id(values: Mapping[str, JSONValue], key: str) -> bool:
    value = _text(values, key)
    return value is not None and re.fullmatch(r"\d{12}", value) is None


def _birth_lookup_missing(values: Mapping[str, JSONValue]) -> bool:
    relevant = {"subject_full_name", "subject_date_of_birth"}
    return bool(relevant & values.keys()) and not all(_present(values, key) for key in relevant)


def _positive_pair_invalid(values: Mapping[str, JSONValue]) -> bool:
    count = _number(values, "new_residents_count")
    area = _number(values, "allocated_area_m2")
    return (count is not None and count <= 0) or (area is not None and area <= 0)


def _below_area_threshold(values: Mapping[str, JSONValue], zone: str, limit: float) -> bool:
    count = _number(values, "new_residents_count")
    area = _number(values, "allocated_area_m2")
    return (
        values.get("hanoi_zone") == zone
        and count is not None
        and count > 0
        and area is not None
        and area / count < limit
    )


def _date_order_invalid(values: Mapping[str, JSONValue]) -> bool:
    start = _text(values, "temporary_start_date")
    end = _text(values, "temporary_end_date")
    if start is None or end is None:
        return False
    try:
        return date.fromisoformat(end) <= date.fromisoformat(start)
    except ValueError:
        return False


RULE_HANDLERS: Mapping[str, RulePredicate] = {
    "BIRTH-SCOPE-001": lambda v: (
        _present(v, "requested_variant") and v["requested_variant"] != "birth_certificate_copy"
    ),
    "BIRTH-SCOPE-002": lambda v: (
        v.get("intent") in {"new_birth_registration", "birth_reregistration", "birth_correction"}
    ),
    "BIRTH-REQ-001": lambda v: (
        "requester_full_name" in v and not _present(v, "requester_full_name")
    ),
    "BIRTH-ID-001": lambda v: _is_bad_personal_id(v, "requester_personal_id"),
    "BIRTH-LOOKUP-001": _birth_lookup_missing,
    "BIRTH-AUTH-001": lambda v: (
        v.get("requester_type") == "authorized_person"
        and v.get("authorization_document_missing") is True
    ),
    "BIRTH-POST-001": lambda v: (
        v.get("submission_channel") == "postal" and v.get("certified_copies_missing") is True
    ),
    "BIRTH-FILE-001": lambda v: (
        v.get("submission_channel") == "online"
        and _present(v, "uploaded_document_quality")
        and v.get("uploaded_document_quality") != "clear_complete_intact"
    ),
    "BIRTH-FOREIGN-001": lambda v: v.get("foreign_issued_document_present") is True,
    "HOUSE-REQ-001": lambda v: v.get("mau_02_missing") is True,
    "HOUSE-ID-001": lambda v: _is_bad_personal_id(v, "requester_personal_id"),
    "HOUSE-AREA-001": _positive_pair_invalid,
    "HOUSE-ZONE-001": lambda v: "hanoi_zone" in v and not _present(v, "hanoi_zone"),
    "HOUSE-THRESHOLD-INNER": lambda v: _below_area_threshold(v, "inner_city", 15),
    "HOUSE-THRESHOLD-SUBURBAN": lambda v: _below_area_threshold(v, "suburban", 8),
    "HOUSE-CONFIRM-001": lambda _v: True,
    "HOUSE-CONSIST-001": lambda v: (
        _number(v, "remaining_floor_area_m2") is not None
        and _number(v, "floor_area_m2") is not None
        and _number(v, "remaining_floor_area_m2") > _number(v, "floor_area_m2")  # type: ignore[operator]
    ),
    "TEMP-SCOPE-001": lambda v: v.get("registration_mode") in {"by_list", "armed_forces"},
    "TEMP-FORM-001": lambda v: v.get("ct01_missing") is True,
    "TEMP-ID-001": lambda v: _is_bad_personal_id(v, "applicant_personal_id"),
    "TEMP-MINOR-001": lambda v: (
        v.get("applicant_is_minor") is True and v.get("minor_consent_present") is False
    ),
    "TEMP-DATE-001": _date_order_invalid,
    "TEMP-HOUSE-001": lambda v: (
        v.get("legal_dwelling_data_retrievable") is False
        and v.get("legal_dwelling_document_present") is False
    ),
    "TEMP-RENT-001": lambda v: (
        v.get("dwelling_basis") in {"rented", "borrowed", "accommodated"}
        and v.get("document_marked_not_notarized") is True
    ),
    "TEMP-FEE-ONLINE": lambda v: (
        v.get("submission_channel") == "online"
        and v.get("registration_mode") == "individual_or_household"
        and v.get("fee_exemption_claimed") is False
    ),
    "TEMP-FEE-DIRECT": lambda v: (
        v.get("submission_channel") == "direct"
        and v.get("registration_mode") == "individual_or_household"
        and v.get("fee_exemption_claimed") is False
    ),
    "TEMP-CITIZENSHIP-001": lambda v: v.get("newly_naturalized_or_restored_citizenship") is True,
}


class RuleEngine:
    """Validate drafts without executing catalog condition strings."""

    def __init__(self, repository: ProcedureRepository, *, today: date | None = None) -> None:
        self._repository = repository
        self._today = today or date.today()

    def validate(
        self,
        procedure_code: ProcedureCode | str,
        values: Mapping[str, JSONValue],
        *,
        context_signals: Mapping[str, JSONValue] | None = None,
        context_origins: Mapping[str, RuleInputOrigin | str] | None = None,
        confirmed_context_signal_ids: Collection[str] = (),
        trusted_adapter_signal_ids: Collection[str] = (),
    ) -> ValidationResult:
        code = ProcedureCode(procedure_code)
        evaluated_values = dict(values)
        known_context_ids = {item.input_id for item in self._repository.rule_inputs_for(code)}
        misplaced_context = evaluated_values.keys() & known_context_ids
        if misplaced_context:
            raise ValueError(
                "Rule-context inputs must be passed separately with provenance: "
                f"{sorted(misplaced_context)}"
            )
        confirmed_ids = set(confirmed_context_signal_ids)
        trusted_adapter_ids = set(trusted_adapter_signal_ids)
        if not all(isinstance(item, str) and item for item in confirmed_ids | trusted_adapter_ids):
            raise ValueError("Promoted context signal IDs must be non-empty strings")
        if confirmed_ids & trusted_adapter_ids:
            raise ValueError("A context signal cannot use two promotion paths")
        if context_origins and not context_signals:
            raise ValueError("Context origins require matching context signals")
        if not context_signals and (confirmed_ids or trusted_adapter_ids):
            raise ValueError("Cannot promote a context signal that was not supplied")
        if context_signals:
            if context_origins is None or set(context_origins) != set(context_signals):
                raise ValueError("Every context signal requires one declared origin")
            promoted_ids = confirmed_ids | trusted_adapter_ids
            if promoted_ids - set(context_signals):
                raise ValueError("Cannot promote a context signal that was not supplied")
            duplicated = evaluated_values.keys() & context_signals.keys()
            if duplicated:
                raise ValueError(
                    f"Context signals must not duplicate form fields: {sorted(duplicated)}"
                )
            for input_id, value in context_signals.items():
                try:
                    origin = RuleInputOrigin(context_origins[input_id])
                except ValueError as exc:
                    raise ValueError(
                        f"Unknown rule-context origin {context_origins[input_id]!r}"
                    ) from exc
                self.validate_context_signal(
                    code,
                    input_id,
                    value,
                    origin=origin,
                )
                if origin in _TEXT_CONTEXT_ORIGINS and input_id not in confirmed_ids:
                    raise ValueError(
                        f"Text-derived context signal {input_id!r} requires confirmation"
                    )
                if origin in _TEXT_CONTEXT_ORIGINS and input_id in trusted_adapter_ids:
                    raise ValueError(
                        f"Text-derived context signal {input_id!r} cannot use adapter trust"
                    )
                if origin in _ADAPTER_CONTEXT_ORIGINS and input_id not in trusted_adapter_ids:
                    raise ValueError(
                        f"Adapter context signal {input_id!r} requires trusted provenance"
                    )
                if origin in _ADAPTER_CONTEXT_ORIGINS and input_id in confirmed_ids:
                    raise ValueError(
                        f"Adapter context signal {input_id!r} cannot use text confirmation"
                    )
            evaluated_values.update(context_signals)
        issues: list[ValidationIssue] = []
        passed: list[str] = []
        for rule in self._repository.rules_for(code):
            handler = RULE_HANDLERS.get(rule.rule_id)
            if handler is None:
                raise RuntimeError(f"Missing deterministic handler for {rule.rule_id}")
            if handler(evaluated_values):
                issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        field_id=self._field_for_rule(rule.rule_id),
                        severity=rule.severity,
                        message=rule.message,
                        suggestion=rule.suggestion,
                        source_ids=rule.source_ids,
                    )
                )
            else:
                passed.append(rule.rule_id)

        issue_ids = {issue.rule_id for issue in issues}
        if issue_ids & {"BIRTH-SCOPE-001", "BIRTH-SCOPE-002"}:
            status = ValidationStatus.OUT_OF_SCOPE
        elif any(issue.severity is IssueSeverity.ERROR for issue in issues):
            status = ValidationStatus.NEEDS_CORRECTION
        elif any(issue.severity is IssueSeverity.NEEDS_REVIEW for issue in issues):
            status = ValidationStatus.NEEDS_OFFICIAL_REVIEW
        else:
            status = ValidationStatus.READY_TO_SUBMIT

        source_ids = tuple(dict.fromkeys(source for issue in issues for source in issue.source_ids))
        if not source_ids:
            source_ids = self._repository.get_by_code(code).source_ids
        return ValidationResult(
            procedure_code=code,
            status=status,
            issues=tuple(issues),
            passed_checks=tuple(passed),
            source_ids=source_ids,
        )

    def validate_context_signal(
        self,
        procedure_code: ProcedureCode | str,
        input_id: str,
        value: JSONValue,
        *,
        origin: RuleInputOrigin | str,
    ) -> None:
        """Validate one non-form rule input and its catalog-declared origin.

        Origin equality alone is not provenance.  ``validate`` separately
        requires confirmation for text-derived candidates or trusted-adapter
        promotion for document/derived inputs before rules can consume them.
        """

        code = ProcedureCode(procedure_code)
        inputs = {item.input_id: item for item in self._repository.rule_inputs_for(code)}
        try:
            item = inputs[input_id]
        except KeyError as exc:
            raise ValueError(f"Unknown rule-context input {input_id!r}") from exc

        try:
            actual_origin = RuleInputOrigin(origin)
        except ValueError as exc:
            raise ValueError(f"Unknown rule-context origin {origin!r}") from exc
        if actual_origin is not item.origin:
            raise ValueError(
                f"Rule-context input {input_id!r} requires origin {item.origin.value!r}"
            )

        if item.field_type is FieldType.STRING and not isinstance(value, str):
            raise ValueError(f"{input_id} must be a string")
        if item.field_type is FieldType.BOOLEAN and not isinstance(value, bool):
            raise ValueError(f"{input_id} must be a boolean")
        if item.field_type is FieldType.INTEGER and (
            isinstance(value, bool) or not isinstance(value, int)
        ):
            raise ValueError(f"{input_id} must be an integer")
        if item.field_type is FieldType.NUMBER and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError(f"{input_id} must be a number")
        if item.field_type is FieldType.DATE:
            if not isinstance(value, str):
                raise ValueError(f"{input_id} must be an ISO date")
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(f"{input_id} must be an ISO date") from exc
        if item.field_type is FieldType.ENUM and value not in item.values:
            raise ValueError(f"{input_id} has an unsupported value")

    def missing_fields(
        self, procedure_code: ProcedureCode | str, values: Mapping[str, JSONValue]
    ) -> tuple[str, ...]:
        code = ProcedureCode(procedure_code)
        missing: list[str] = []
        for field in self._repository.fields_for(code):
            if self._is_required(field, values) and not _present(values, field.field_id):
                missing.append(field.field_id)
        return tuple(missing)

    def validate_field_value(
        self, procedure_code: ProcedureCode | str, field_id: str, value: JSONValue
    ) -> None:
        fields = {field.field_id: field for field in self._repository.fields_for(procedure_code)}
        try:
            field = fields[field_id]
        except KeyError as exc:
            raise ValueError(f"Unknown field {field_id!r}") from exc

        if field.field_type is FieldType.STRING and not isinstance(value, str):
            raise ValueError(f"{field_id} must be a string")
        if field.field_type is FieldType.BOOLEAN and not isinstance(value, bool):
            raise ValueError(f"{field_id} must be a boolean")
        if field.field_type is FieldType.INTEGER and (
            isinstance(value, bool) or not isinstance(value, int)
        ):
            raise ValueError(f"{field_id} must be an integer")
        if field.field_type is FieldType.NUMBER and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError(f"{field_id} must be a number")
        if field.field_type is FieldType.ENUM and value not in field.values:
            raise ValueError(f"{field_id} has an unsupported value")
        if field.field_type is FieldType.DATE:
            if not isinstance(value, str):
                raise ValueError(f"{field_id} must be an ISO date")
            try:
                parsed = date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(f"{field_id} must be an ISO date") from exc
            if "date_of_birth" in field_id and parsed > self._today:
                raise ValueError(f"{field_id} cannot be in the future")
        if field.pattern is not None and (
            not isinstance(value, str) or re.fullmatch(field.pattern, value) is None
        ):
            raise ValueError(f"{field_id} does not match the required format")
        if field.minimum is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float)) or value < field.minimum
        ):
            raise ValueError(f"{field_id} is below the minimum")

    @staticmethod
    def _is_required(field: FieldDefinition, values: Mapping[str, JSONValue]) -> bool:
        requirement = field.requirement
        if requirement in {
            "required",
            "required_for_lookup",
            "required_for_area_check",
            "required_for_threshold",
            "required_declaration",
        }:
            return True
        if requirement == "required_or_identity_document":
            return not _present(values, "requester_id_document_type")
        if requirement == "conditional_minor":
            return values.get("applicant_is_minor") is True
        if requirement == "conditional_fallback":
            if field.field_id == "legal_dwelling_document_present":
                return values.get("legal_dwelling_data_retrievable") is False
            return not _present(values, "requester_personal_id")
        if requirement == "conditional":
            if field.field_id == "requester_id_document_type":
                return not _present(values, "requester_personal_id")
            if field.field_id == "authorization_relationship":
                return values.get("requester_type") == "authorized_person"
            if field.field_id == "owner_or_householder_consent":
                return values.get("dwelling_basis") in {
                    "rented",
                    "borrowed",
                    "accommodated",
                    "join_family_household",
                }
        return False

    @staticmethod
    def _field_for_rule(rule_id: str) -> str | None:
        mapping = {
            "BIRTH-REQ-001": "requester_full_name",
            "BIRTH-ID-001": "requester_personal_id",
            "BIRTH-LOOKUP-001": "subject_full_name",
            "BIRTH-AUTH-001": "authorization_relationship",
            "BIRTH-POST-001": "submission_channel",
            "BIRTH-FILE-001": "submission_channel",
            "HOUSE-ID-001": "requester_personal_id",
            "HOUSE-AREA-001": "allocated_area_m2",
            "HOUSE-ZONE-001": "hanoi_zone",
            "HOUSE-THRESHOLD-INNER": "allocated_area_m2",
            "HOUSE-THRESHOLD-SUBURBAN": "allocated_area_m2",
            "HOUSE-CONSIST-001": "remaining_floor_area_m2",
            "TEMP-SCOPE-001": "registration_mode",
            "TEMP-ID-001": "applicant_personal_id",
            "TEMP-MINOR-001": "minor_consent_present",
            "TEMP-DATE-001": "temporary_end_date",
            "TEMP-HOUSE-001": "legal_dwelling_document_present",
            "TEMP-RENT-001": "dwelling_basis",
            "TEMP-FEE-ONLINE": "submission_channel",
            "TEMP-FEE-DIRECT": "submission_channel",
        }
        return mapping.get(rule_id)
