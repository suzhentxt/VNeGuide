"""Catalog-derived schema and validation for LLM extraction output.

This module intentionally owns only the provider-facing wire shape.  Procedure
fields and constraints are loaded from the reviewed data package instead of
being copied into Python enums or models.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import MappingProxyType
from typing import Any

JsonScalar = str | int | float | bool

_CLASSIFICATIONS = frozenset({"supported", "unsupported", "ambiguous"})
_FIELD_TYPES = frozenset({"string", "date", "enum", "integer", "number", "boolean"})
_ROOT_KEYS = frozenset({"classification", "procedure_code", "clarification_question", "fields"})
_FIELD_KEYS = frozenset({"field_id", "value", "evidence"})
_PRONOUN_ONLY_NAME_VALUES = frozenset(
    {"tôi", "mình", "chúng tôi", "chúng mình", "tớ", "con tôi", "con của tôi"}
)
_UNINFORMATIVE_ENUM_EVIDENCE = frozenset(
    {"vâng", "dạ", "đồng ý", "tôi đồng ý", "mình đồng ý", "được", "ừ", "ừm", "ok", "okay"}
)
_POSSESSIVE_RELATION_REFERENCE = re.compile(
    r"^(?:cho\s+)?(?:con|bố|ba|cha|mẹ|má|vợ|chồng|ông|bà|anh|chị|em)(?:\s+của)?\s+tôi$"
)
_PHRASE_EDGE_CHARACTERS = " \t\r\n.,!?;:…'\"“”‘’()[]{}"


class ExtractionSchemaError(ValueError):
    """A provider response or catalog entry violates the extraction contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """One reviewed field constraint for one procedure."""

    procedure_code: str
    field_id: str
    label: str
    field_type: str
    values: tuple[str, ...] = ()
    pattern: str | None = None
    minimum: int | float | None = None
    maximum: int | float | None = None

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> FieldSpec:
        try:
            procedure_code = record["procedure_code"]
            field_id = record["field_id"]
            label = record["label"]
            field_type = record["type"]
        except KeyError as exc:
            raise ExtractionSchemaError(
                "invalid_catalog", f"Field catalog entry is missing {exc.args[0]!r}."
            ) from exc

        if not all(isinstance(value, str) and value for value in (procedure_code, field_id, label)):
            raise ExtractionSchemaError(
                "invalid_catalog", "Procedure code, field ID, and label must be non-empty strings."
            )
        if field_type not in _FIELD_TYPES:
            raise ExtractionSchemaError(
                "invalid_catalog", f"Unsupported catalog field type: {field_type!r}."
            )

        raw_values = record.get("values", ())
        if not isinstance(raw_values, Sequence) or isinstance(raw_values, (str, bytes)):
            raise ExtractionSchemaError("invalid_catalog", "Enum values must be an array.")
        values = tuple(raw_values)
        if any(not isinstance(value, str) or not value for value in values):
            raise ExtractionSchemaError(
                "invalid_catalog", "Every enum value must be a non-empty string."
            )
        if field_type == "enum" and not values:
            raise ExtractionSchemaError("invalid_catalog", "Enum fields must declare values.")

        pattern = record.get("pattern")
        if pattern is not None and not isinstance(pattern, str):
            raise ExtractionSchemaError("invalid_catalog", "Field pattern must be a string.")
        if pattern is not None:
            try:
                re.compile(pattern, flags=re.ASCII)
            except re.error as exc:
                raise ExtractionSchemaError(
                    "invalid_catalog", f"Invalid pattern for {field_id!r}."
                ) from exc

        minimum = record.get("minimum")
        maximum = record.get("maximum")
        for bound in (minimum, maximum):
            if bound is not None and (
                type(bound) not in (int, float) or not math.isfinite(float(bound))
            ):
                raise ExtractionSchemaError(
                    "invalid_catalog", "Numeric bounds must be finite numbers."
                )

        return cls(
            procedure_code=procedure_code,
            field_id=field_id,
            label=label,
            field_type=field_type,
            values=values,
            pattern=pattern,
            minimum=minimum,
            maximum=maximum,
        )

    def value_schema(self) -> dict[str, Any]:
        """Return a portable Structured Outputs fragment for this field's value.

        Catalog patterns and numeric bounds are enforced locally after the
        provider returns.  Keeping the provider schema to basic types and enum
        avoids model-family differences in supported JSON Schema keywords.
        """

        if self.field_type == "enum":
            schema: dict[str, Any] = {"type": "string", "enum": list(self.values)}
        elif self.field_type == "date":
            schema = {"type": "string"}
        else:
            type_mapping = {
                "string": "string",
                "integer": "integer",
                "number": "number",
                "boolean": "boolean",
            }
            json_type = type_mapping[self.field_type]
            schema = {"type": json_type}

        return schema


@dataclass(frozen=True, slots=True)
class ProcedureSpec:
    """Routing metadata loaded from an approved procedure pack."""

    code: str
    name: str
    aliases: tuple[str, ...] = ()
    in_scope: tuple[str, ...] = ()
    needs_official_review: tuple[str, ...] = ()
    out_of_scope: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExtractionCatalog:
    """Immutable view of extractable fields and routing metadata."""

    _fields_by_procedure: Mapping[str, Mapping[str, FieldSpec]]
    _procedures: Mapping[str, ProcedureSpec]

    @classmethod
    def from_records(
        cls,
        field_records: Iterable[Mapping[str, Any]],
        procedure_records: Iterable[Mapping[str, Any]] = (),
    ) -> ExtractionCatalog:
        mutable_fields: dict[str, dict[str, FieldSpec]] = {}
        for record in field_records:
            spec = FieldSpec.from_record(record)
            procedure_fields = mutable_fields.setdefault(spec.procedure_code, {})
            if spec.field_id in procedure_fields:
                raise ExtractionSchemaError(
                    "invalid_catalog",
                    f"Duplicate field {spec.field_id!r} for procedure {spec.procedure_code!r}.",
                )
            procedure_fields[spec.field_id] = spec

        if not mutable_fields:
            raise ExtractionSchemaError("invalid_catalog", "Field catalog cannot be empty.")

        procedures: dict[str, ProcedureSpec] = {}
        for record in procedure_records:
            code = record.get("procedure_code")
            name = record.get("procedure_name")
            routing = record.get("routing", {})
            aliases = routing.get("aliases", ()) if isinstance(routing, Mapping) else ()
            scope = record.get("scope", {})
            if not isinstance(scope, Mapping):
                raise ExtractionSchemaError("invalid_catalog", "Procedure scope must be an object.")
            in_scope = scope.get("in_scope", ())
            needs_official_review = scope.get("needs_official_review", ())
            out_of_scope = scope.get("out_of_scope", ())
            if not isinstance(code, str) or not code or not isinstance(name, str) or not name:
                raise ExtractionSchemaError(
                    "invalid_catalog", "Procedure records require code and name strings."
                )
            if not isinstance(aliases, Sequence) or isinstance(aliases, (str, bytes)):
                raise ExtractionSchemaError(
                    "invalid_catalog", "Procedure aliases must be an array."
                )
            if any(not isinstance(alias, str) or not alias for alias in aliases):
                raise ExtractionSchemaError(
                    "invalid_catalog", "Procedure aliases must be non-empty strings."
                )
            for scope_name, entries in (
                ("in_scope", in_scope),
                ("needs_official_review", needs_official_review),
                ("out_of_scope", out_of_scope),
            ):
                if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
                    raise ExtractionSchemaError(
                        "invalid_catalog", f"Procedure {scope_name} must be an array."
                    )
                if any(not isinstance(entry, str) or not entry for entry in entries):
                    raise ExtractionSchemaError(
                        "invalid_catalog",
                        f"Procedure {scope_name} entries must be non-empty strings.",
                    )
            if code in procedures:
                raise ExtractionSchemaError(
                    "invalid_catalog", f"Duplicate procedure metadata for {code!r}."
                )
            procedures[code] = ProcedureSpec(
                code=code,
                name=name,
                aliases=tuple(aliases),
                in_scope=tuple(in_scope),
                needs_official_review=tuple(needs_official_review),
                out_of_scope=tuple(out_of_scope),
            )

        if set(procedures) != set(mutable_fields):
            raise ExtractionSchemaError(
                "invalid_catalog",
                "Field catalog and procedure metadata must contain exactly the same codes.",
            )

        frozen_fields = MappingProxyType(
            {
                code: MappingProxyType(dict(sorted(fields.items())))
                for code, fields in sorted(mutable_fields.items())
            }
        )
        return cls(frozen_fields, MappingProxyType(dict(sorted(procedures.items()))))

    @classmethod
    def from_data_package(cls, data_directory: Path) -> ExtractionCatalog:
        """Load extraction metadata from a VNeGuide data package directory."""

        catalog_directory = data_directory / "catalog"
        field_records = _load_json(catalog_directory / "field_catalog.json")
        if not isinstance(field_records, list):
            raise ExtractionSchemaError("invalid_catalog", "Field catalog root must be an array.")

        procedure_records: list[Mapping[str, Any]] = []
        approved_codes: set[str] = set()
        procedure_directory = catalog_directory / "procedure_packs"
        for path in sorted(procedure_directory.glob("*.json")):
            record = _load_json(path)
            if not isinstance(record, Mapping):
                raise ExtractionSchemaError(
                    "invalid_catalog", f"Procedure pack {path.name!r} must be an object."
                )
            if record.get("status") == "approved":
                procedure_records.append(record)
                code = record.get("procedure_code")
                if isinstance(code, str):
                    approved_codes.add(code)

        field_codes = {
            record.get("procedure_code") for record in field_records if isinstance(record, Mapping)
        }
        if field_codes != approved_codes:
            raise ExtractionSchemaError(
                "unapproved_procedure",
                "Every field-catalog procedure must have one approved procedure pack.",
            )
        return cls.from_records(field_records, procedure_records)

    @property
    def procedure_codes(self) -> tuple[str, ...]:
        return tuple(self._fields_by_procedure)

    @property
    def procedures(self) -> tuple[ProcedureSpec, ...]:
        return tuple(self._procedures.values())

    @property
    def field_count(self) -> int:
        return sum(len(fields) for fields in self._fields_by_procedure.values())

    def fields_for(self, procedure_code: str) -> tuple[FieldSpec, ...]:
        try:
            return tuple(self._fields_by_procedure[procedure_code].values())
        except KeyError as exc:
            raise ExtractionSchemaError(
                "unknown_procedure", f"Unknown procedure code: {procedure_code!r}."
            ) from exc

    def field(self, procedure_code: str, field_id: str) -> FieldSpec:
        try:
            return self._fields_by_procedure[procedure_code][field_id]
        except KeyError as exc:
            raise ExtractionSchemaError(
                "unknown_field",
                f"Field {field_id!r} is not defined for procedure {procedure_code!r}.",
            ) from exc


@dataclass(frozen=True, slots=True)
class ValidatedExtraction:
    """Validated provider output, still independent of domain workflow state."""

    classification: str
    procedure_code: str | None
    fields: Mapping[str, JsonScalar]
    evidence: Mapping[str, str]
    clarification_question: str | None


def build_extraction_json_schema(catalog: ExtractionCatalog) -> dict[str, Any]:
    """Build an OpenAI-compatible strict JSON Schema from reviewed catalog fields."""

    item_variants: list[dict[str, Any]] = []
    for procedure_code in catalog.procedure_codes:
        for spec in catalog.fields_for(procedure_code):
            item_variants.append(
                {
                    "type": "object",
                    "description": f"{procedure_code}: {spec.label}",
                    "properties": {
                        "field_id": {"type": "string", "enum": [spec.field_id]},
                        "value": spec.value_schema(),
                        "evidence": {
                            "type": "string",
                            "description": "Verbatim evidence from the current user message.",
                        },
                    },
                    "required": ["field_id", "value", "evidence"],
                    "additionalProperties": False,
                }
            )

    return {
        "type": "object",
        "properties": {
            "classification": {
                "type": "string",
                "enum": ["supported", "unsupported", "ambiguous"],
            },
            "procedure_code": {
                "type": ["string", "null"],
                "enum": [*catalog.procedure_codes, None],
            },
            "clarification_question": {"type": ["string", "null"]},
            "fields": {
                "type": "array",
                "items": {"anyOf": item_variants},
            },
        },
        "required": ["classification", "procedure_code", "clarification_question", "fields"],
        "additionalProperties": False,
    }


def validate_extraction_payload(
    payload: Mapping[str, Any], *, message: str, catalog: ExtractionCatalog
) -> ValidatedExtraction:
    """Validate provider output without coercing, defaulting, or inferring values."""

    if not isinstance(payload, Mapping):
        raise ExtractionSchemaError("invalid_root", "Extraction output must be an object.")
    _require_exact_keys(payload, _ROOT_KEYS, "root")

    classification = payload["classification"]
    procedure_code = payload["procedure_code"]
    clarification_question = payload["clarification_question"]
    raw_fields = payload["fields"]

    if not isinstance(classification, str) or classification not in _CLASSIFICATIONS:
        raise ExtractionSchemaError("invalid_classification", "Unknown extraction classification.")
    if procedure_code is not None and not isinstance(procedure_code, str):
        raise ExtractionSchemaError("invalid_procedure", "Procedure code must be a string or null.")
    if clarification_question is not None and not isinstance(clarification_question, str):
        raise ExtractionSchemaError(
            "invalid_clarification", "Clarification question must be a string or null."
        )
    if not isinstance(raw_fields, list):
        raise ExtractionSchemaError("invalid_fields", "Fields must be an array.")

    if classification == "supported":
        if procedure_code not in catalog.procedure_codes:
            raise ExtractionSchemaError(
                "invalid_procedure", "Supported output requires a catalog procedure code."
            )
        if clarification_question is not None:
            raise ExtractionSchemaError(
                "invalid_clarification", "Supported output cannot ask an intent clarification."
            )
    else:
        if procedure_code is not None or raw_fields:
            raise ExtractionSchemaError(
                "unsafe_non_supported",
                "Unsupported or ambiguous output must have a null code and no fields.",
            )
        if classification == "ambiguous":
            if clarification_question is None or not clarification_question.strip():
                raise ExtractionSchemaError(
                    "invalid_clarification", "Ambiguous output requires one clarification question."
                )
        elif clarification_question is not None:
            raise ExtractionSchemaError(
                "invalid_clarification", "Unsupported output cannot ask an intent clarification."
            )

    if clarification_question is not None and len(clarification_question) > 500:
        raise ExtractionSchemaError(
            "invalid_clarification", "Clarification question exceeds the safe length limit."
        )

    fields: dict[str, JsonScalar] = {}
    evidence_by_field: dict[str, str] = {}
    for raw_field in raw_fields:
        if not isinstance(raw_field, Mapping):
            raise ExtractionSchemaError("invalid_field", "Every extracted field must be an object.")
        _require_exact_keys(raw_field, _FIELD_KEYS, "field")
        field_id = raw_field["field_id"]
        value = raw_field["value"]
        evidence = raw_field["evidence"]
        if not isinstance(field_id, str) or not field_id:
            raise ExtractionSchemaError("invalid_field", "Field ID must be a non-empty string.")
        assert procedure_code is not None
        spec = catalog.field(procedure_code, field_id)
        if field_id in fields:
            raise ExtractionSchemaError("duplicate_field", f"Duplicate field: {field_id!r}.")
        if not isinstance(evidence, str) or not evidence.strip() or len(evidence) > 500:
            raise ExtractionSchemaError(
                "invalid_evidence", "Field evidence must be a short, non-empty string."
            )
        if not _contains_evidence(message, evidence):
            raise ExtractionSchemaError(
                "unverifiable_evidence", f"Evidence for {field_id!r} is absent from the message."
            )

        _validate_value(spec, value)
        if _is_pronoun_only_name(spec, value) or _is_uninformative_enum_evidence(spec, evidence):
            continue
        if not _evidence_supports_value(spec, value, evidence):
            raise ExtractionSchemaError(
                "inconsistent_evidence",
                f"Evidence does not support the extracted value for {field_id!r}.",
            )
        fields[field_id] = value
        evidence_by_field[field_id] = evidence

    return ValidatedExtraction(
        classification=classification,
        procedure_code=procedure_code,
        fields=MappingProxyType(fields),
        evidence=MappingProxyType(evidence_by_field),
        clarification_question=clarification_question,
    )


def decode_provider_payload(raw: object) -> Mapping[str, Any]:
    """Decode a provider value while rejecting non-standard JSON constants."""

    if isinstance(raw, Mapping):
        return raw
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ExtractionSchemaError("malformed_json", "Provider output is not UTF-8.") from exc
    if not isinstance(raw, str):
        raise ExtractionSchemaError(
            "invalid_root", "Provider output must be a JSON object or encoded JSON object."
        )
    try:
        decoded = json.loads(
            raw,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ExtractionSchemaError("malformed_json", "Provider output is not valid JSON.") from exc
    if not isinstance(decoded, Mapping):
        raise ExtractionSchemaError("invalid_root", "Provider JSON root must be an object.")
    return decoded


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(
                stream,
                parse_constant=_reject_json_constant,
                object_pairs_hook=_reject_duplicate_pairs,
            )
    except OSError as exc:
        raise ExtractionSchemaError("catalog_io", f"Cannot read catalog file {path}.") from exc
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ExtractionSchemaError("invalid_catalog", f"Invalid JSON in {path}.") from exc


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Unsupported JSON constant: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    decoded: dict[str, Any] = {}
    for key, value in pairs:
        if key in decoded:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        decoded[key] = value
    return decoded


def _require_exact_keys(
    mapping: Mapping[str, Any], expected: frozenset[str], location: str
) -> None:
    actual = frozenset(mapping)
    if actual != expected:
        raise ExtractionSchemaError(
            "unexpected_keys",
            f"{location.capitalize()} keys differ from the strict extraction contract.",
        )


def _validate_value(spec: FieldSpec, value: object) -> None:
    if spec.field_type in {"string", "date", "enum"}:
        if not isinstance(value, str) or not value:
            raise ExtractionSchemaError("invalid_value", f"{spec.field_id!r} must be a string.")
        if spec.field_type == "enum" and value not in spec.values:
            raise ExtractionSchemaError(
                "invalid_value", f"{spec.field_id!r} has an unknown enum value."
            )
        if spec.field_type == "date":
            try:
                parsed = date.fromisoformat(value)
            except ValueError as exc:
                raise ExtractionSchemaError(
                    "invalid_value", f"{spec.field_id!r} must be an ISO date."
                ) from exc
            if parsed.isoformat() != value:
                raise ExtractionSchemaError(
                    "invalid_value", f"{spec.field_id!r} must use canonical YYYY-MM-DD."
                )
        if spec.pattern is not None and re.fullmatch(spec.pattern, value, flags=re.ASCII) is None:
            raise ExtractionSchemaError(
                "invalid_value", f"{spec.field_id!r} does not match its catalog pattern."
            )
    elif spec.field_type == "integer":
        if type(value) is not int:
            raise ExtractionSchemaError("invalid_value", f"{spec.field_id!r} must be an integer.")
    elif spec.field_type == "number":
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise ExtractionSchemaError(
                "invalid_value", f"{spec.field_id!r} must be a finite number."
            )
    elif spec.field_type == "boolean" and type(value) is not bool:
        raise ExtractionSchemaError("invalid_value", f"{spec.field_id!r} must be a boolean.")

    if spec.minimum is not None and value < spec.minimum:  # type: ignore[operator]
        raise ExtractionSchemaError(
            "invalid_value", f"{spec.field_id!r} is below its catalog minimum."
        )
    if spec.maximum is not None and value > spec.maximum:  # type: ignore[operator]
        raise ExtractionSchemaError(
            "invalid_value", f"{spec.field_id!r} is above its catalog maximum."
        )


def _contains_evidence(message: str, evidence: str) -> bool:
    return _normalise_text(evidence) in _normalise_text(message)


def _is_pronoun_only_name(spec: FieldSpec, value: object) -> bool:
    return (
        spec.field_id.endswith("_full_name")
        and isinstance(value, str)
        and _normalise_phrase(value) in _PRONOUN_ONLY_NAME_VALUES
    )


def _is_uninformative_enum_evidence(spec: FieldSpec, evidence: str) -> bool:
    if spec.field_type != "enum":
        return False
    phrase = _normalise_phrase(evidence)
    return (
        phrase in _UNINFORMATIVE_ENUM_EVIDENCE
        or _POSSESSIVE_RELATION_REFERENCE.fullmatch(phrase) is not None
    )


def _evidence_supports_value(spec: FieldSpec, value: JsonScalar, evidence: str) -> bool:
    if spec.field_type == "string":
        normalised_value = _normalise_text(str(value))
        normalised_evidence = _normalise_text(evidence)
        return (
            re.search(rf"(?<!\w){re.escape(normalised_value)}(?!\w)", normalised_evidence)
            is not None
        )
    if spec.field_type in {"integer", "number"}:
        candidate_pattern = r"(?<![\d.,])[-+]?\d+(?:[.,]\d+)?(?![\d.,])"
        for match in re.finditer(candidate_pattern, evidence):
            candidate = match.group(0)
            try:
                parsed_number = float(candidate.replace(",", "."))
            except ValueError:
                continue
            if parsed_number == float(value):
                return True
        return False
    if spec.field_type == "date":
        assert isinstance(value, str)
        expected = date.fromisoformat(value)
        candidates = re.findall(r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}", evidence)
        for candidate in candidates:
            separator = "/" if "/" in candidate else "-"
            parts = candidate.split(separator)
            try:
                if len(parts[0]) == 4:
                    parsed_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                else:
                    parsed_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
            except (ValueError, IndexError):
                continue
            if parsed_date == expected:
                return True
        natural_candidates = re.findall(
            r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
            evidence,
            flags=re.IGNORECASE,
        )
        for day_text, month_text, year_text in natural_candidates:
            try:
                parsed_date = date(int(year_text), int(month_text), int(day_text))
            except ValueError:
                continue
            if parsed_date == expected:
                return True
        return False
    return True


def _normalise_text(value: str) -> str:
    normalised = unicodedata.normalize("NFC", value).casefold()
    return " ".join(normalised.split())


def _normalise_phrase(value: str) -> str:
    return _normalise_text(value).strip(_PHRASE_EDGE_CHARACTERS)
