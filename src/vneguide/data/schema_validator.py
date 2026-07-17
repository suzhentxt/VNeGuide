"""Small JSON Schema validator for the keywords used by this repository.

The project schemas intentionally use a narrow Draft 2020-12 subset. Keeping
this validator dependency-free lets data checks run before an LLM SDK is
installed. Unsupported schema keywords remain annotations and are ignored.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .errors import SchemaValidationError


@dataclass(frozen=True, slots=True)
class SchemaViolation:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _matches_type(value: object, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, Mapping)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def validate_json_schema(
    instance: object,
    schema: Mapping[str, Any],
    path: str = "$",
) -> tuple[SchemaViolation, ...]:
    violations: list[SchemaViolation] = []

    declared_type = schema.get("type")
    if declared_type is not None:
        expected_types: Sequence[str]
        if isinstance(declared_type, str):
            expected_types = (declared_type,)
        elif isinstance(declared_type, list):
            expected_types = tuple(item for item in declared_type if isinstance(item, str))
        else:
            expected_types = ()
        if expected_types and not any(_matches_type(instance, item) for item in expected_types):
            violations.append(
                SchemaViolation(path, f"expected type {' or '.join(expected_types)}")
            )
            return tuple(violations)

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and instance not in enum_values:
        violations.append(SchemaViolation(path, f"value {instance!r} is not in enum"))

    if isinstance(instance, Mapping):
        required = schema.get("required", [])
        if isinstance(required, list):
            for name in required:
                if isinstance(name, str) and name not in instance:
                    violations.append(SchemaViolation(path, f"missing required property {name!r}"))

        properties = schema.get("properties", {})
        if isinstance(properties, Mapping):
            for name, value in instance.items():
                child_schema = properties.get(name)
                if isinstance(child_schema, Mapping):
                    violations.extend(
                        validate_json_schema(value, child_schema, f"{path}.{name}")
                    )
                elif schema.get("additionalProperties") is False:
                    violations.append(
                        SchemaViolation(path, f"unexpected property {name!r}")
                    )

    if isinstance(instance, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            for index, value in enumerate(instance):
                violations.extend(validate_json_schema(value, item_schema, f"{path}[{index}]"))

    if isinstance(instance, str):
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, instance) is None:
            violations.append(SchemaViolation(path, f"does not match pattern {pattern!r}"))

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if isinstance(instance, float) and not math.isfinite(instance):
            violations.append(SchemaViolation(path, "must be a finite number"))
            return tuple(violations)
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and instance < minimum:
            violations.append(SchemaViolation(path, f"must be at least {minimum}"))
        if isinstance(maximum, (int, float)) and instance > maximum:
            violations.append(SchemaViolation(path, f"must be at most {maximum}"))

    return tuple(violations)


def assert_json_schema(instance: object, schema: Mapping[str, Any]) -> None:
    violations = validate_json_schema(instance, schema)
    if violations:
        raise SchemaValidationError(violations)
