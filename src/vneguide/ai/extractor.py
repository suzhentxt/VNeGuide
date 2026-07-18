"""Retry-bounded structured extraction orchestration."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType

from vneguide.ai.prompts import build_extraction_prompt
from vneguide.ai.providers.base import (
    LLMProvider,
    ProviderConfigurationError,
    ProviderError,
    ProviderRefusal,
    ProviderTimeout,
    StructuredRequest,
)
from vneguide.ai.schemas import (
    ExtractionCatalog,
    ExtractionSchemaError,
    JsonScalar,
    build_extraction_json_schema,
    decode_provider_payload,
    validate_extraction_payload,
)


def _empty_mapping() -> Mapping[str, JsonScalar]:
    return MappingProxyType({})


def _empty_text_mapping() -> Mapping[str, str]:
    return MappingProxyType({})


@dataclass(frozen=True, slots=True)
class ExtractionOutcome:
    """Safe AI-local extraction result pending the shared domain adapter.

    ``status=fallback`` is a technical failure and is deliberately distinct
    from the semantic ``classification=unsupported`` result.
    """

    status: str
    classification: str | None
    procedure_code: str | None
    fields: Mapping[str, JsonScalar]
    evidence: Mapping[str, str]
    clarification_question: str | None
    attempts: int
    error_code: str | None = None
    context_signals: Mapping[str, JsonScalar] = field(default_factory=_empty_mapping)
    context_evidence: Mapping[str, str] = field(default_factory=_empty_text_mapping)
    context_origins: Mapping[str, str] = field(default_factory=_empty_text_mapping)

    @property
    def succeeded(self) -> bool:
        return self.status == "success"


@dataclass(frozen=True, slots=True)
class ExtractionTurnContext:
    """Bounded, non-PII metadata for resolving a follow-up user turn."""

    active_procedure_code: str
    expected_field_id: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.active_procedure_code, str)
            or not self.active_procedure_code.strip()
            or len(self.active_procedure_code) > 64
        ):
            raise ValueError("active_procedure_code must be a short non-empty string")
        if self.expected_field_id is not None and (
            not isinstance(self.expected_field_id, str)
            or not self.expected_field_id.strip()
            or len(self.expected_field_id) > 128
        ):
            raise ValueError("expected_field_id must be a short non-empty string or None")


class StructuredExtractor:
    """Call an LLM through a provider and validate every returned value."""

    def __init__(
        self,
        provider: LLMProvider,
        catalog: ExtractionCatalog,
        *,
        max_attempts: int = 2,
        timeout_seconds: float = 20.0,
        max_input_chars: int = 8_000,
    ) -> None:
        if type(max_attempts) is not int or not 1 <= max_attempts <= 2:
            raise ValueError("max_attempts must be 1 or 2")
        if (
            type(timeout_seconds) not in (int, float)
            or not math.isfinite(float(timeout_seconds))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive number")
        if type(max_input_chars) is not int or max_input_chars <= 0:
            raise ValueError("max_input_chars must be a positive integer")
        self._provider = provider
        self._catalog = catalog
        self._max_attempts = max_attempts
        self._request_schema = build_extraction_json_schema(catalog)
        self._system_prompt = build_extraction_prompt(catalog)
        self._timeout_seconds = timeout_seconds
        self._max_input_chars = max_input_chars

    @property
    def response_schema(self) -> Mapping[str, object]:
        """Return the schema supplied to every provider call."""

        return deepcopy(self._request_schema)

    def extract(
        self,
        message: str,
        *,
        context: ExtractionTurnContext | None = None,
    ) -> ExtractionOutcome:
        """Extract one Vietnamese user turn, retrying only safe failure classes."""

        if (
            not isinstance(message, str)
            or not message.strip()
            or len(message) > self._max_input_chars
        ):
            return self._fallback(attempts=0, error_code="invalid_input")
        try:
            message.encode("utf-8")
        except UnicodeEncodeError:
            return self._fallback(attempts=0, error_code="invalid_input")
        if context is not None and not self._context_is_valid(context):
            return self._fallback(attempts=0, error_code="invalid_context")

        user_prompt = self._user_prompt(message, context)

        last_error_code = "provider_error"

        for attempt in range(1, self._max_attempts + 1):
            try:
                request = StructuredRequest(
                    system_prompt=self._system_prompt,
                    user_prompt=user_prompt,
                    json_schema=deepcopy(self._request_schema),
                    schema_name="vneguide_extraction",
                    timeout_seconds=self._timeout_seconds,
                )
                raw_payload = self._provider.generate_structured(request)
                payload = decode_provider_payload(raw_payload)
                validated = validate_extraction_payload(
                    payload,
                    message=message,
                    catalog=self._catalog,
                )
                return ExtractionOutcome(
                    status="success",
                    classification=validated.classification,
                    procedure_code=validated.procedure_code,
                    fields=validated.fields,
                    evidence=validated.evidence,
                    context_signals=validated.context_signals,
                    context_evidence=validated.context_evidence,
                    context_origins=validated.context_origins,
                    clarification_question=validated.clarification_question,
                    attempts=attempt,
                )
            except ProviderConfigurationError:
                return self._fallback(attempts=attempt, error_code="provider_configuration")
            except ProviderRefusal:
                return self._fallback(attempts=attempt, error_code="provider_refusal")
            except ProviderTimeout:
                last_error_code = "provider_timeout"
            except ProviderError as exc:
                last_error_code = "provider_error"
                if not exc.retryable:
                    return self._fallback(attempts=attempt, error_code=last_error_code)
            except ExtractionSchemaError:
                last_error_code = "malformed_output"

            if attempt == self._max_attempts:
                return self._fallback(attempts=attempt, error_code=last_error_code)

        raise AssertionError("bounded extraction loop terminated unexpectedly")

    def _context_is_valid(self, context: ExtractionTurnContext) -> bool:
        if context.active_procedure_code not in self._catalog.procedure_codes:
            return False
        if context.expected_field_id is None:
            return True
        try:
            self._catalog.field(context.active_procedure_code, context.expected_field_id)
        except ExtractionSchemaError:
            return False
        return True

    @staticmethod
    def _user_prompt(message: str, context: ExtractionTurnContext | None) -> str:
        envelope: dict[str, object] = {
            "current_user_message": message,
            "conversation_context": None,
        }
        if context is not None:
            envelope["conversation_context"] = {
                "active_procedure_code": context.active_procedure_code,
                "expected_field_id": context.expected_field_id,
            }
        return json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _fallback(*, attempts: int, error_code: str) -> ExtractionOutcome:
        return ExtractionOutcome(
            status="fallback",
            classification=None,
            procedure_code=None,
            fields=MappingProxyType({}),
            evidence=MappingProxyType({}),
            clarification_question=None,
            attempts=attempts,
            error_code=error_code,
            context_signals=MappingProxyType({}),
            context_evidence=MappingProxyType({}),
            context_origins=MappingProxyType({}),
        )


__all__ = [
    "ExtractionOutcome",
    "ExtractionTurnContext",
    "StructuredExtractor",
]
