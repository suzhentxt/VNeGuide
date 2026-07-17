"""Tests for provider-neutral structured extraction."""

from __future__ import annotations

import json
import math
import unittest
from http.client import IncompleteRead
from pathlib import Path
from typing import ClassVar, cast
from urllib.request import Request as HTTPRequest

from vneguide.ai.config import LLMConfig, build_llm_provider, load_llm_config
from vneguide.ai.extractor import StructuredExtractor
from vneguide.ai.providers import (
    MockLLMProvider,
    OpenAIResponsesProvider,
    ProviderConfigurationError,
    ProviderError,
    ProviderRefusal,
    ProviderTimeout,
    StructuredRequest,
)
from vneguide.ai.providers.openai import _NoRedirectHandler
from vneguide.ai.schemas import (
    ExtractionCatalog,
    ExtractionSchemaError,
    build_extraction_json_schema,
    decode_provider_payload,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _payload(
    *,
    classification: str = "supported",
    procedure_code: str | None = "2.000635",
    fields: list[dict[str, object]] | None = None,
    clarification_question: str | None = None,
) -> dict[str, object]:
    return {
        "classification": classification,
        "procedure_code": procedure_code,
        "clarification_question": clarification_question,
        "fields": [] if fields is None else fields,
    }


class StructuredExtractorTests(unittest.TestCase):
    catalog: ClassVar[ExtractionCatalog]

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = ExtractionCatalog.from_data_package(REPOSITORY_ROOT / "data")

    def test_intent_fixture_contract_runs_through_validated_mock_pipeline(self) -> None:
        fixture_path = REPOSITORY_ROOT / "tests" / "evals" / "intent_cases.jsonl"
        with fixture_path.open("r", encoding="utf-8") as stream:
            cases = [json.loads(line) for line in stream if line.strip()]

        self.assertGreaterEqual(len(cases), 12)
        self.assertEqual(
            {case["expected_classification"] for case in cases},
            {"supported", "unsupported", "ambiguous"},
        )

        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                classification = case["expected_classification"]
                message = case["message"]
                fields = [
                    {"field_id": field_id, "value": value, "evidence": message}
                    for field_id, value in case["expected_fields"].items()
                ]
                clarification = (
                    "Bạn cần thực hiện thủ tục nào?" if classification == "ambiguous" else None
                )
                provider = MockLLMProvider(
                    [
                        _payload(
                            classification=classification,
                            procedure_code=case["expected_procedure_code"],
                            fields=fields,
                            clarification_question=clarification,
                        )
                    ]
                )
                outcome = StructuredExtractor(provider, self.catalog).extract(message)

                self.assertTrue(outcome.succeeded)
                self.assertEqual(outcome.classification, classification)
                self.assertEqual(outcome.procedure_code, case["expected_procedure_code"])
                self.assertEqual(dict(outcome.fields), case["expected_fields"])

    def test_every_call_receives_strict_catalog_schema(self) -> None:
        provider = MockLLMProvider([_payload()])
        extractor = StructuredExtractor(provider, self.catalog, timeout_seconds=7.5)

        extractor.extract("Tôi muốn xin lại giấy khai sinh.")

        self.assertEqual(len(provider.calls), 1)
        request = provider.calls[0]
        self.assertEqual(request.timeout_seconds, 7.5)
        self.assertEqual(request.json_schema["type"], "object")
        self.assertFalse(request.json_schema["additionalProperties"])
        self.assertEqual(
            set(request.json_schema["required"]),
            {"classification", "procedure_code", "clarification_question", "fields"},
        )
        self.assertEqual(request.schema_name, "vneguide_extraction")
        self.assertIn("Đăng ký khai sinh mới hoặc đăng ký lại", request.system_prompt)
        self.assertIn("Thực hiện thủ tục đăng ký thường trú 1.004222", request.system_prompt)
        self.assertIn("Đăng ký tạm trú theo danh sách", request.system_prompt)

    def test_callers_cannot_mutate_the_extractor_schema(self) -> None:
        provider = MockLLMProvider([_payload()])
        extractor = StructuredExtractor(provider, self.catalog)
        public_schema = cast(dict[str, object], extractor.response_schema)
        public_schema["type"] = "array"

        extractor.extract("Tôi muốn xin lại giấy khai sinh.")

        self.assertEqual(provider.calls[0].json_schema["type"], "object")

    def test_retries_malformed_output_then_returns_valid_result(self) -> None:
        provider = MockLLMProvider(
            [
                {"classification": "supported"},
                _payload(
                    fields=[
                        {
                            "field_id": "copies_requested",
                            "value": 2,
                            "evidence": "2 bản",
                        }
                    ]
                ),
            ]
        )

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Tôi cần xin giấy khai sinh 2 bản."
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.attempts, 2)
        self.assertEqual(dict(outcome.fields), {"copies_requested": 2})
        self.assertEqual(len(provider.calls), 2)

    def test_accepts_literal_string_and_normalised_date_with_verbatim_evidence(self) -> None:
        provider = MockLLMProvider(
            [
                _payload(
                    fields=[
                        {
                            "field_id": "subject_full_name",
                            "value": "Người Mẫu A",
                            "evidence": "Người Mẫu A",
                        },
                        {
                            "field_id": "subject_date_of_birth",
                            "value": "2020-02-01",
                            "evidence": "01/02/2020",
                        },
                    ]
                )
            ]
        )

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Xin bản sao khai sinh cho Người Mẫu A, sinh ngày 01/02/2020."
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.fields["subject_date_of_birth"], "2020-02-01")

    def test_accepts_natural_vietnamese_date_evidence(self) -> None:
        provider = MockLLMProvider(
            [
                _payload(
                    fields=[
                        {
                            "field_id": "subject_date_of_birth",
                            "value": "2020-02-01",
                            "evidence": "ngày 1 tháng 2 năm 2020",
                        }
                    ]
                )
            ]
        )

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Người cần bản sao sinh ngày 1 tháng 2 năm 2020."
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.fields["subject_date_of_birth"], "2020-02-01")

    def test_malformed_output_is_bounded_and_falls_back_safely(self) -> None:
        provider = MockLLMProvider([{}, {}])

        outcome = StructuredExtractor(provider, self.catalog).extract("Xin giấy khai sinh.")

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.error_code, "malformed_output")
        self.assertEqual(outcome.attempts, 2)
        self.assertIsNone(outcome.classification)
        self.assertIsNone(outcome.procedure_code)
        self.assertEqual(dict(outcome.fields), {})

    def test_unhashable_classification_is_malformed_not_an_uncaught_type_error(self) -> None:
        malformed = _payload()
        malformed["classification"] = []
        provider = MockLLMProvider([malformed, malformed])

        outcome = StructuredExtractor(provider, self.catalog).extract("Xin giấy khai sinh.")

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.error_code, "malformed_output")
        self.assertEqual(outcome.attempts, 2)

    def test_timeout_is_retried_once_and_not_misclassified_as_unsupported(self) -> None:
        provider = MockLLMProvider([ProviderTimeout("slow"), ProviderTimeout("still slow")])

        outcome = StructuredExtractor(provider, self.catalog).extract("Đăng ký tạm trú.")

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.error_code, "provider_timeout")
        self.assertIsNone(outcome.classification)
        self.assertEqual(len(provider.calls), 2)

    def test_provider_error_retry_policy_is_bounded(self) -> None:
        retrying_provider = MockLLMProvider(
            [ProviderError("temporary", retryable=True), _payload()]
        )
        retrying_outcome = StructuredExtractor(retrying_provider, self.catalog).extract(
            "Xin bản sao khai sinh."
        )
        self.assertTrue(retrying_outcome.succeeded)
        self.assertEqual(retrying_outcome.attempts, 2)

        stopping_provider = MockLLMProvider(
            [ProviderError("permanent", retryable=False), _payload()]
        )
        stopping_outcome = StructuredExtractor(stopping_provider, self.catalog).extract(
            "Xin bản sao khai sinh."
        )
        self.assertFalse(stopping_outcome.succeeded)
        self.assertEqual(stopping_outcome.error_code, "provider_error")
        self.assertEqual(stopping_outcome.attempts, 1)
        self.assertEqual(len(stopping_provider.calls), 1)

    def test_refusal_and_configuration_errors_do_not_retry(self) -> None:
        for error, code in (
            (ProviderRefusal("refused"), "provider_refusal"),
            (ProviderConfigurationError("missing"), "provider_configuration"),
        ):
            with self.subTest(code=code):
                provider = MockLLMProvider([error, _payload()])
                outcome = StructuredExtractor(provider, self.catalog).extract("Xin Mẫu số 02.")
                self.assertEqual(outcome.error_code, code)
                self.assertEqual(outcome.attempts, 1)
                self.assertEqual(len(provider.calls), 1)

    def test_rejects_cross_procedure_unknown_duplicate_and_unverifiable_fields(self) -> None:
        invalid_fields: tuple[list[dict[str, object]], ...] = (
            [
                {
                    "field_id": "copies_requested",
                    "value": 2,
                    "evidence": "2 bản",
                }
            ],
            [{"field_id": "requested_variant", "value": "x", "evidence": "x"}],
            [
                {"field_id": "submission_channel", "value": "online", "evidence": "online"},
                {"field_id": "submission_channel", "value": "online", "evidence": "online"},
            ],
            [{"field_id": "submission_channel", "value": "online", "evidence": "online"}],
        )
        messages = (
            "Tôi đăng ký tạm trú và cần 2 bản.",
            "Tôi cần x.",
            "Tôi đăng ký tạm trú online.",
            "Tôi đăng ký tạm trú trực tiếp.",
        )
        for fields, message in zip(invalid_fields, messages, strict=True):
            with self.subTest(fields=fields):
                provider = MockLLMProvider(
                    [
                        _payload(procedure_code="1.004194", fields=fields),
                        _payload(procedure_code="1.004194", fields=fields),
                    ]
                )
                outcome = StructuredExtractor(provider, self.catalog).extract(message)
                self.assertFalse(outcome.succeeded)
                self.assertEqual(outcome.error_code, "malformed_output")

    def test_rejects_type_pattern_enum_bound_and_date_violations(self) -> None:
        invalid_cases: tuple[tuple[str, dict[str, object], str], ...] = (
            (
                "1.013314",
                {"field_id": "new_residents_count", "value": True, "evidence": "đúng"},
                "đúng",
            ),
            (
                "1.004194",
                {"field_id": "applicant_is_minor", "value": 1, "evidence": "1"},
                "1",
            ),
            (
                "2.000635",
                {
                    "field_id": "requester_personal_id",
                    "value": "１２３４５６７８９０１２",
                    "evidence": "１２３４５６７８９０１２",
                },
                "１２３４５６７８９０１２",
            ),
            (
                "1.004194",
                {
                    "field_id": "applicant_date_of_birth",
                    "value": "2025-02-30",
                    "evidence": "2025-02-30",
                },
                "2025-02-30",
            ),
            (
                "1.013314",
                {"field_id": "new_residents_count", "value": 0, "evidence": "0"},
                "0",
            ),
            (
                "1.004194",
                {"field_id": "submission_channel", "value": "postal", "evidence": "postal"},
                "postal",
            ),
            (
                "1.013314",
                {"field_id": "allocated_area_m2", "value": math.inf, "evidence": "inf"},
                "inf",
            ),
            (
                "2.000635",
                {
                    "field_id": "subject_full_name",
                    "value": "A",
                    "evidence": "Trần An",
                },
                "Trần An",
            ),
        )
        for procedure_code, field, message in invalid_cases:
            with self.subTest(field=field):
                provider = MockLLMProvider(
                    [
                        _payload(procedure_code=procedure_code, fields=[field]),
                        _payload(procedure_code=procedure_code, fields=[field]),
                    ]
                )
                outcome = StructuredExtractor(provider, self.catalog).extract(message)
                self.assertFalse(outcome.succeeded)

    def test_non_supported_output_cannot_smuggle_fields_or_a_procedure(self) -> None:
        unsafe = _payload(
            classification="unsupported",
            procedure_code="2.000635",
            fields=[{"field_id": "copies_requested", "value": 1, "evidence": "1"}],
        )
        provider = MockLLMProvider([unsafe, unsafe])

        outcome = StructuredExtractor(provider, self.catalog).extract("Đăng ký khai sinh 1 bé.")

        self.assertFalse(outcome.succeeded)
        self.assertEqual(dict(outcome.fields), {})
        self.assertIsNone(outcome.procedure_code)

    def test_empty_input_returns_fallback_without_calling_provider(self) -> None:
        provider = MockLLMProvider([_payload()])
        outcome = StructuredExtractor(provider, self.catalog).extract("  ")
        self.assertEqual(outcome.error_code, "invalid_input")
        self.assertEqual(outcome.attempts, 0)
        self.assertEqual(provider.calls, [])

    def test_input_and_retry_configuration_are_bounded(self) -> None:
        provider = MockLLMProvider([_payload()])
        outcome = StructuredExtractor(provider, self.catalog, max_input_chars=3).extract("abcd")
        self.assertEqual(outcome.error_code, "invalid_input")
        self.assertEqual(provider.calls, [])

        invalid_unicode = StructuredExtractor(provider, self.catalog).extract("\ud800")
        self.assertEqual(invalid_unicode.error_code, "invalid_input")
        self.assertEqual(provider.calls, [])

        for kwargs in (
            {"max_attempts": 3},
            {"timeout_seconds": math.nan},
            {"max_input_chars": 0},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                StructuredExtractor(provider, self.catalog, **kwargs)

    def test_malformed_json_constants_duplicates_and_depth_are_rejected(self) -> None:
        invalid_json_values = (
            '{"classification":"supported","procedure_code":"2.000635",'
            '"clarification_question":null,"fields":[NaN]}',
            '{"classification":"supported","classification":"unsupported"}',
            "[" * 2_000 + "]" * 2_000,
        )
        for invalid_json in invalid_json_values:
            with self.subTest(prefix=invalid_json[:30]), self.assertRaises(ExtractionSchemaError):
                decode_provider_payload(invalid_json)

    def test_config_is_lazy_safe_without_api_key(self) -> None:
        config = load_llm_config({})
        self.assertEqual(config.provider, "mock")
        self.assertIsNone(config.model)
        self.assertIsNone(config.api_key)

        secret_config = load_llm_config(
            {
                "VNEGUIDE_LLM_PROVIDER": "openai",
                "VNEGUIDE_MODEL": "test-model",
                "VNEGUIDE_API_KEY": "do-not-print",
            }
        )
        self.assertNotIn("do-not-print", repr(secret_config))

    def test_provider_factory_validates_selection_and_openai_credentials(self) -> None:
        mock = build_llm_provider(LLMConfig(provider="mock", model=None, api_key=None))
        self.assertIsInstance(mock, MockLLMProvider)

        openai = build_llm_provider(
            LLMConfig(provider="openai", model="test-model", api_key="test-key")
        )
        self.assertIsInstance(openai, OpenAIResponsesProvider)

        for config in (
            LLMConfig(provider="openai", model=None, api_key=None),
            LLMConfig(provider="unknown", model=None, api_key=None),
        ):
            with (
                self.subTest(provider=config.provider),
                self.assertRaises(ProviderConfigurationError),
            ):
                build_llm_provider(config)

    def test_catalog_requires_matching_procedure_metadata(self) -> None:
        with self.assertRaises(ExtractionSchemaError):
            ExtractionCatalog.from_records(
                [
                    {
                        "procedure_code": "example",
                        "field_id": "name",
                        "label": "Tên",
                        "type": "string",
                    }
                ]
            )


class _FakeHTTPResponse:
    def __init__(self, payload: MappingLike, status: int = 200) -> None:
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]

    def close(self) -> None:
        self.closed = True


MappingLike = dict[str, object]


class OpenAIResponsesProviderTests(unittest.TestCase):
    def test_sends_strict_responses_payload_and_decodes_output_text(self) -> None:
        expected = _payload()
        api_response: MappingLike = {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(expected)}],
                }
            ],
        }
        captured: dict[str, object] = {}

        def opener(request: object, *, timeout: float) -> _FakeHTTPResponse:
            captured["request"] = request
            captured["timeout"] = timeout
            return _FakeHTTPResponse(api_response)

        provider = OpenAIResponsesProvider(api_key="test-key", model="test-model", opener=opener)
        request = StructuredRequest(
            system_prompt="system",
            user_prompt="user",
            json_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            schema_name="test_schema",
            timeout_seconds=4.0,
        )

        result = provider.generate_structured(request)

        self.assertEqual(result, expected)
        self.assertEqual(captured["timeout"], 4.0)
        http_request = cast(HTTPRequest, captured["request"])
        request_body = cast(bytes, http_request.data)
        sent = json.loads(request_body.decode("utf-8"))
        self.assertEqual(sent["model"], "test-model")
        self.assertFalse(sent["store"])
        self.assertEqual(sent["text"]["format"]["type"], "json_schema")
        self.assertTrue(sent["text"]["format"]["strict"])
        self.assertNotIn("test-key", json.dumps(sent))

    def test_wraps_timeout_and_refusal(self) -> None:
        def timeout_opener(request: object, *, timeout: float) -> object:
            raise TimeoutError

        provider = OpenAIResponsesProvider(
            api_key="test-key", model="test-model", opener=timeout_opener
        )
        request = StructuredRequest("system", "user", {}, "schema", 1.0)
        with self.assertRaises(ProviderTimeout):
            provider.generate_structured(request)

        refusal_response: MappingLike = {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "refusal", "refusal": "no"}],
                }
            ],
        }
        refusing_provider = OpenAIResponsesProvider(
            api_key="test-key",
            model="test-model",
            opener=lambda request, timeout: _FakeHTTPResponse(refusal_response),
        )
        with self.assertRaises(ProviderRefusal):
            refusing_provider.generate_structured(request)

    def test_rejects_duplicate_keys_in_structured_output(self) -> None:
        duplicate_output_response: MappingLike = {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"classification":"supported","classification":"unsupported"}',
                        }
                    ],
                }
            ],
        }
        provider = OpenAIResponsesProvider(
            api_key="test-key",
            model="test-model",
            opener=lambda request, timeout: _FakeHTTPResponse(duplicate_output_response),
        )
        request = StructuredRequest("system", "user", {}, "schema", 1.0)

        with self.assertRaises(ProviderError):
            provider.generate_structured(request)

    def test_rejects_unknown_status_and_wraps_truncated_http_response(self) -> None:
        request = StructuredRequest("system", "user", {}, "schema", 1.0)
        invalid_statuses: tuple[object, ...] = ("unexpected", [], {})
        for invalid_status in invalid_statuses:
            with self.subTest(status=invalid_status):
                unknown_status_response: MappingLike = {
                    "status": invalid_status,
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": json.dumps(_payload())}],
                        }
                    ],
                }
                provider = OpenAIResponsesProvider(
                    api_key="test-key",
                    model="test-model",
                    opener=lambda request, timeout, response=unknown_status_response: (
                        _FakeHTTPResponse(response)
                    ),
                )
                with self.assertRaises(ProviderError):
                    provider.generate_structured(request)

        class TruncatedResponse:
            status = 200

            def read(self, size: int = -1) -> bytes:
                raise IncompleteRead(b"{", 10)

            def close(self) -> None:
                pass

        truncated_provider = OpenAIResponsesProvider(
            api_key="test-key",
            model="test-model",
            opener=lambda request, timeout: TruncatedResponse(),
        )
        with self.assertRaises(ProviderError):
            truncated_provider.generate_structured(request)

    def test_rejects_untrusted_api_url_and_oversized_response(self) -> None:
        with self.assertRaises(ProviderConfigurationError):
            OpenAIResponsesProvider(
                api_key="test-key",
                model="test-model",
                api_url="https://example.com/v1/responses",
            )

        class OversizedResponse:
            status = 200

            def read(self, size: int = -1) -> bytes:
                return b"x" * size

            def close(self) -> None:
                pass

        provider = OpenAIResponsesProvider(
            api_key="test-key",
            model="test-model",
            opener=lambda request, timeout: OversizedResponse(),
        )
        request = StructuredRequest("system", "user", {}, "schema", 1.0)
        with self.assertRaises(ProviderError):
            provider.generate_structured(request)

    def test_rejects_header_unsafe_api_key_without_echoing_it(self) -> None:
        unsafe_key = "test-key\nDO-NOT-LEAK"
        with self.assertRaises(ProviderConfigurationError) as context:
            OpenAIResponsesProvider(api_key=unsafe_key, model="test-model")

        self.assertNotIn("DO-NOT-LEAK", str(context.exception))

    def test_default_transport_disables_http_redirects(self) -> None:
        handler = _NoRedirectHandler()
        redirected = handler.redirect_request(
            None,
            None,
            302,
            "Found",
            {},
            "https://example.com/steal-key",
        )
        self.assertIsNone(redirected)

    def test_schema_is_catalog_derived_not_a_stale_intent_enum(self) -> None:
        catalog = ExtractionCatalog.from_data_package(REPOSITORY_ROOT / "data")
        schema = build_extraction_json_schema(catalog)
        procedure_enum = schema["properties"]["procedure_code"]["enum"]
        self.assertEqual(set(procedure_enum), {"2.000635", "1.013314", "1.004194", None})
        self.assertNotIn("marriage_extract", json.dumps(schema))
        self.assertNotIn("death_extract", json.dumps(schema))
        schema_text = json.dumps(schema)
        for unsupported_keyword in ('"format"', '"pattern"', '"minimum"', '"maximum"'):
            self.assertNotIn(unsupported_keyword, schema_text)


if __name__ == "__main__":
    unittest.main()
