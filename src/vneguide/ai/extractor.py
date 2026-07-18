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
    InformationRequest,
    JsonScalar,
    build_extraction_json_schema,
    decode_provider_payload,
    validate_extraction_payload,
)
from vneguide.domain import QATopic
from vneguide.language import InputSource, LanguageNormalizer, NormalizationResult


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
    reply: str | None = None
    error_code: str | None = None
    context_signals: Mapping[str, JsonScalar] = field(default_factory=_empty_mapping)
    context_evidence: Mapping[str, str] = field(default_factory=_empty_text_mapping)
    context_origins: Mapping[str, str] = field(default_factory=_empty_text_mapping)
    information_request: InformationRequest | None = None
    invalid_field_id: str | None = None
    normalization: NormalizationResult | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == "success"


@dataclass(frozen=True, slots=True)
class ExtractionTurnContext:
    """Bounded, non-PII metadata for resolving a follow-up user turn."""

    active_procedure_code: str
    expected_field_id: str | None = None
    confirmation_required: bool = False
    recent_information_topics: tuple[QATopic, ...] = ()
    recent_information_procedure_code: str | None = None

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
        if type(self.confirmation_required) is not bool:
            raise ValueError("confirmation_required must be a boolean")
        if self.confirmation_required and self.expected_field_id is not None:
            raise ValueError("confirmation_required context cannot include an expected field")
        if not isinstance(self.recent_information_topics, tuple):
            raise ValueError("recent_information_topics must be a tuple")
        if (
            len(self.recent_information_topics) > 3
            or len(set(self.recent_information_topics)) != len(self.recent_information_topics)
            or any(not isinstance(topic, QATopic) for topic in self.recent_information_topics)
        ):
            raise ValueError(
                "recent_information_topics must contain at most three unique QATopic values"
            )
        if self.recent_information_procedure_code is not None and (
            not isinstance(self.recent_information_procedure_code, str)
            or not self.recent_information_procedure_code.strip()
            or len(self.recent_information_procedure_code) > 64
        ):
            raise ValueError(
                "recent_information_procedure_code must be a short non-empty string or None"
            )


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
        normalizer: LanguageNormalizer | None = None,
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
        self._normalizer = normalizer or LanguageNormalizer()

    @property
    def response_schema(self) -> Mapping[str, object]:
        """Return the schema supplied to every provider call."""

        return deepcopy(self._request_schema)

    def extract(
        self,
        message: str,
        *,
        context: ExtractionTurnContext | None = None,
        input_source: InputSource = InputSource.TEXT,
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

        normalization = self._normalizer.normalize(message, source=input_source)
        if normalization.ambiguities:
            return ExtractionOutcome(
                status="success",
                classification="ambiguous",
                procedure_code=None,
                fields=MappingProxyType({}),
                evidence=MappingProxyType({}),
                clarification_question=normalization.clarification_prompt(),
                attempts=0,
                normalization=normalization,
            )

        normalized_message = normalization.normalized_text
        user_prompt = self._user_prompt(normalized_message, context)

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
                    message=normalized_message,
                    catalog=self._catalog,
                )
                evidence = self._remap_evidence(validated.evidence, normalization)
                context_evidence = self._remap_evidence(
                    validated.context_evidence,
                    normalization,
                )
                return ExtractionOutcome(
                    status="success",
                    classification=validated.classification,
                    procedure_code=validated.procedure_code,
                    fields=validated.fields,
                    evidence=evidence,
                    context_signals=validated.context_signals,
                    context_evidence=context_evidence,
                    context_origins=validated.context_origins,
                    clarification_question=validated.clarification_question,
                    attempts=attempt,
                    reply=validated.reply,
                    information_request=validated.information_request,
                    normalization=normalization,
                )
            except ProviderConfigurationError:
                return self._fallback(
                    attempts=attempt,
                    error_code="provider_configuration",
                    normalization=normalization,
                )
            except ProviderRefusal:
                return self._fallback(
                    attempts=attempt,
                    error_code="provider_refusal",
                    normalization=normalization,
                )
            except ProviderTimeout:
                last_error_code = "provider_timeout"
            except ProviderError as exc:
                last_error_code = "provider_error"
                if not exc.retryable:
                    return self._fallback(
                        attempts=attempt,
                        error_code=last_error_code,
                        normalization=normalization,
                    )
            except ExtractionSchemaError as exc:
                if exc.code == "invalid_value":
                    return self._fallback(
                        attempts=attempt,
                        error_code="invalid_value",
                        invalid_field_id=exc.field_id,
                        normalization=normalization,
                    )
                last_error_code = "malformed_output"

            if attempt == self._max_attempts:
                return self._fallback(
                    attempts=attempt,
                    error_code=last_error_code,
                    normalization=normalization,
                )

        raise AssertionError("bounded extraction loop terminated unexpectedly")

    def _context_is_valid(self, context: ExtractionTurnContext) -> bool:
        if context.active_procedure_code not in self._catalog.procedure_codes:
            return False
        if (
            context.recent_information_procedure_code is not None
            and context.recent_information_procedure_code not in self._catalog.procedure_codes
        ):
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
                "confirmation_required": context.confirmation_required,
                "recent_information_topics": [
                    topic.value for topic in context.recent_information_topics
                ],
                "recent_information_procedure_code": (context.recent_information_procedure_code),
            }
        return json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _remap_evidence(
        evidence: Mapping[str, str],
        normalization: NormalizationResult,
    ) -> Mapping[str, str]:
        remapped: dict[str, str] = {}
        for key, normalized_evidence in evidence.items():
            raw_evidence = normalization.raw_text_for(normalized_evidence)
            if raw_evidence is None:
                raise ExtractionSchemaError(
                    "unmappable_evidence",
                    f"Normalized evidence for {key!r} cannot be traced to raw input.",
                )
            remapped[key] = raw_evidence
        return MappingProxyType(remapped)

    @staticmethod
    def _fallback(
        *,
        attempts: int,
        error_code: str,
        invalid_field_id: str | None = None,
        normalization: NormalizationResult | None = None,
    ) -> ExtractionOutcome:
        return ExtractionOutcome(
            status="fallback",
            classification=None,
            procedure_code=None,
            fields=MappingProxyType({}),
            evidence=MappingProxyType({}),
            clarification_question=None,
            attempts=attempts,
            reply=None,
            error_code=error_code,
            context_signals=MappingProxyType({}),
            context_evidence=MappingProxyType({}),
            context_origins=MappingProxyType({}),
            information_request=None,
            invalid_field_id=invalid_field_id,
            normalization=normalization,
        )


__all__ = [
    "ExtractionOutcome",
    "ExtractionTurnContext",
    "StructuredExtractor",
]
