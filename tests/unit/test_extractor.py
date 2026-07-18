"""Tests for provider-neutral structured extraction."""

from __future__ import annotations

import json
import math
import unittest
from http.client import IncompleteRead
from pathlib import Path
from typing import ClassVar, cast
from urllib.request import Request as HTTPRequest

from vneguide.ai import InformationRequest
from vneguide.ai.config import LLMConfig, build_llm_provider, load_llm_config
from vneguide.ai.extractor import ExtractionTurnContext, StructuredExtractor
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
from vneguide.domain import QATopic
from vneguide.language import LanguageNormalizer

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _payload(
    *,
    classification: str = "supported",
    procedure_code: str | None = "2.000635",
    fields: list[dict[str, object]] | None = None,
    context_signals: list[dict[str, object]] | None = None,
    clarification_question: str | None = None,
    reply: str | None = None,
    information_request: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "classification": classification,
        "procedure_code": procedure_code,
        "reply": reply,
        "clarification_question": clarification_question,
        "fields": [] if fields is None else fields,
        "context_signals": [] if context_signals is None else context_signals,
        "information_request": information_request,
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
            {"supported", "unsupported", "ambiguous", "informational"},
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
                expected_topics = case.get("expected_topics", [])
                expected_references = case.get("expected_reference_fields", {})
                information_request = (
                    {
                        "topics": expected_topics,
                        "target_field_id": case.get("expected_target_field_id"),
                        "reference_fields": [
                            {
                                "field_id": field_id,
                                "value": value,
                                "evidence": message,
                            }
                            for field_id, value in expected_references.items()
                        ],
                    }
                    if classification == "informational"
                    else None
                )
                provider = MockLLMProvider(
                    [
                        _payload(
                            classification=classification,
                            procedure_code=case["expected_procedure_code"],
                            fields=fields,
                            clarification_question=clarification,
                            information_request=information_request,
                        )
                    ]
                )
                outcome = StructuredExtractor(provider, self.catalog).extract(message)

                self.assertTrue(outcome.succeeded)
                self.assertEqual(outcome.classification, classification)
                self.assertEqual(outcome.procedure_code, case["expected_procedure_code"])
                self.assertEqual(dict(outcome.fields), case["expected_fields"])
                if classification == "informational":
                    assert outcome.information_request is not None
                    self.assertEqual(
                        tuple(topic.value for topic in outcome.information_request.topics),
                        tuple(expected_topics),
                    )
                    self.assertEqual(
                        dict(outcome.information_request.reference_fields),
                        expected_references,
                    )
                else:
                    self.assertIsNone(outcome.information_request)

    def test_dialect_is_normalized_for_model_and_evidence_returns_to_raw_turn(self) -> None:
        raw_message = "tui muốn xin 2 bản giấy khai sanh"
        normalized_message = "tôi muốn xin 2 bản giấy khai sinh"
        provider = MockLLMProvider(
            [
                _payload(
                    fields=[
                        {
                            "field_id": "copies_requested",
                            "value": 2,
                            "evidence": normalized_message,
                        }
                    ]
                )
            ]
        )

        outcome = StructuredExtractor(
            provider,
            self.catalog,
            normalizer=LanguageNormalizer(),
        ).extract(raw_message)

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.fields["copies_requested"], 2)
        self.assertEqual(outcome.evidence["copies_requested"], raw_message)
        self.assertIsNotNone(outcome.normalization)
        envelope = json.loads(provider.calls[0].user_prompt)
        self.assertEqual(envelope["current_user_message"], normalized_message)

    def test_known_language_ambiguity_does_not_call_provider(self) -> None:
        provider = MockLLMProvider([])

        outcome = StructuredExtractor(provider, self.catalog).extract("Tôi cần giấy nhà")

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.classification, "ambiguous")
        self.assertEqual(outcome.attempts, 0)
        self.assertEqual(provider.calls, [])
        self.assertIn("Giấy chứng nhận quyền sử dụng đất", outcome.clarification_question or "")

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
            {
                "classification",
                "procedure_code",
                "reply",
                "clarification_question",
                "fields",
                "context_signals",
                "information_request",
            },
        )
        self.assertEqual(request.schema_name, "vneguide_extraction")
        self.assertIn("Đăng ký khai sinh mới hoặc đăng ký lại", request.system_prompt)
        self.assertIn("Thực hiện thủ tục đăng ký thường trú 1.004222", request.system_prompt)
        self.assertIn("Đăng ký tạm trú theo danh sách", request.system_prompt)
        self.assertIn('Đại từ xưng hô như "tôi"', request.system_prompt)
        self.assertIn('submission_channel="online"', request.system_prompt)
        self.assertIn('câu hiện tại "cho con tôi"', request.system_prompt)

    def test_compact_turn_context_is_sent_without_replacing_current_evidence(self) -> None:
        provider = MockLLMProvider(
            [
                _payload(
                    procedure_code="1.004194",
                    fields=[
                        {
                            "field_id": "submission_channel",
                            "value": "online",
                            "evidence": "trực tuyến",
                        }
                    ],
                )
            ]
        )
        message = "Tôi đăng ký trực tuyến"

        outcome = StructuredExtractor(provider, self.catalog).extract(
            message,
            context=ExtractionTurnContext("1.004194", "registration_mode"),
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.procedure_code, "1.004194")
        self.assertEqual(outcome.fields["submission_channel"], "online")
        envelope = json.loads(provider.calls[0].user_prompt)
        self.assertEqual(envelope["current_user_message"], message)
        self.assertEqual(
            envelope["conversation_context"],
            {
                "active_procedure_code": "1.004194",
                "expected_field_id": "registration_mode",
                "confirmation_required": False,
                "recent_information_topics": [],
                "recent_information_procedure_code": None,
            },
        )
        self.assertNotIn("messages", envelope)

    def test_context_cannot_be_used_as_field_evidence(self) -> None:
        unsafe_payload = _payload(
            procedure_code="1.004194",
            fields=[
                {
                    "field_id": "registration_mode",
                    "value": "individual_or_household",
                    "evidence": "registration_mode",
                }
            ],
        )
        provider = MockLLMProvider([unsafe_payload, unsafe_payload])

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Tôi đồng ý",
            context=ExtractionTurnContext("1.004194", "registration_mode"),
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(dict(outcome.fields), {})
        self.assertEqual(len(provider.calls), 1)

    def test_pronoun_only_person_name_is_safely_discarded(self) -> None:
        unsafe_payload = _payload(
            procedure_code="1.004194",
            fields=[
                {
                    "field_id": "applicant_full_name",
                    "value": "tôi",
                    "evidence": "tôi",
                }
            ],
        )
        provider = MockLLMProvider([unsafe_payload])

        outcome = StructuredExtractor(provider, self.catalog).extract("Tôi muốn đăng ký tạm trú")

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.procedure_code, "1.004194")
        self.assertEqual(dict(outcome.fields), {})
        self.assertEqual(len(provider.calls), 1)

    def test_child_reference_does_not_infer_requester_or_authorization_fields(self) -> None:
        payload = _payload(
            fields=[
                {
                    "field_id": "requester_type",
                    "value": "authorized_person",
                    "evidence": "con tôi",
                },
                {
                    "field_id": "authorization_relationship",
                    "value": "parent",
                    "evidence": "con tôi",
                },
                {
                    "field_id": "copies_requested",
                    "value": 2,
                    "evidence": "2 bản",
                },
            ],
        )
        provider = MockLLMProvider([payload])

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Cho con tôi, tôi cần 2 bản.",
            context=ExtractionTurnContext("2.000635", "requester_type"),
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.procedure_code, "2.000635")
        self.assertEqual(dict(outcome.fields), {"copies_requested": 2})
        self.assertEqual(dict(outcome.evidence), {"copies_requested": "2 bản"})

    def test_generic_agreement_does_not_infer_registration_mode(self) -> None:
        payload = _payload(
            procedure_code="1.004194",
            fields=[
                {
                    "field_id": "registration_mode",
                    "value": "individual_or_household",
                    "evidence": "Tôi đồng ý.",
                },
                {
                    "field_id": "submission_channel",
                    "value": "online",
                    "evidence": "trực tuyến",
                },
            ],
        )
        provider = MockLLMProvider([payload])

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Tôi đồng ý. Tôi đăng ký trực tuyến.",
            context=ExtractionTurnContext("1.004194", "registration_mode"),
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.procedure_code, "1.004194")
        self.assertEqual(dict(outcome.fields), {"submission_channel": "online"})
        self.assertEqual(dict(outcome.evidence), {"submission_channel": "trực tuyến"})

    def test_punctuated_pronoun_name_is_safely_discarded(self) -> None:
        payload = _payload(
            procedure_code="1.004194",
            fields=[
                {
                    "field_id": "applicant_full_name",
                    "value": "Tôi.",
                    "evidence": "Tôi.",
                },
                {
                    "field_id": "submission_channel",
                    "value": "online",
                    "evidence": "trực tuyến",
                },
            ],
        )
        provider = MockLLMProvider([payload])

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Tôi. Tôi đăng ký trực tuyến.",
            context=ExtractionTurnContext("1.004194", "applicant_full_name"),
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.procedure_code, "1.004194")
        self.assertEqual(dict(outcome.fields), {"submission_channel": "online"})
        self.assertEqual(dict(outcome.evidence), {"submission_channel": "trực tuyến"})

    def test_invalid_context_is_rejected_before_calling_the_provider(self) -> None:
        provider = MockLLMProvider([_payload()])
        extractor = StructuredExtractor(provider, self.catalog)
        invalid_contexts = (
            ExtractionTurnContext("9.999999"),
            ExtractionTurnContext("1.004194", "unknown_field"),
            ExtractionTurnContext("1.004194", recent_information_procedure_code="9.999999"),
        )

        for context in invalid_contexts:
            with self.subTest(context=context):
                outcome = extractor.extract("Tôi đồng ý", context=context)
                self.assertEqual(outcome.error_code, "invalid_context")
                self.assertEqual(outcome.attempts, 0)
        self.assertEqual(provider.calls, [])

        for invalid_code in ("", "x" * 65):
            with self.subTest(value=invalid_code), self.assertRaises(ValueError):
                ExtractionTurnContext(invalid_code)

        for invalid_type in (None, 42):
            with self.subTest(value=invalid_type), self.assertRaises(ValueError):
                ExtractionTurnContext(cast(str, invalid_type))

        with self.assertRaisesRegex(ValueError, "confirmation_required"):
            ExtractionTurnContext(
                "1.004194",
                confirmation_required=cast(bool, "yes"),
            )
        with self.assertRaisesRegex(ValueError, "expected field"):
            ExtractionTurnContext(
                "1.004194",
                "registration_mode",
                confirmation_required=True,
            )
        with self.assertRaisesRegex(ValueError, "recent_information_procedure_code"):
            ExtractionTurnContext(
                "1.004194",
                recent_information_procedure_code="",
            )

    def test_catalog_locks_three_codes_and_separates_rule_context_origins(self) -> None:
        self.assertEqual(
            set(self.catalog.procedure_codes),
            {"2.000635", "1.013314", "1.004194"},
        )
        self.assertEqual(self.catalog.rule_context_count, 10)
        birth_extractable = {
            item.input_id for item in self.catalog.extractable_rule_contexts_for("2.000635")
        }
        temp_extractable = {
            item.input_id for item in self.catalog.extractable_rule_contexts_for("1.004194")
        }
        self.assertEqual(birth_extractable, {"intent"})
        self.assertEqual(
            temp_extractable,
            {"newly_naturalized_or_restored_citizenship"},
        )
        self.assertNotIn("ct01_missing", temp_extractable)
        self.assertNotIn("requested_variant", birth_extractable)

    def test_short_answer_uses_context_but_current_message_remains_evidence_source(self) -> None:
        provider = MockLLMProvider(
            [
                _payload(
                    procedure_code="1.004194",
                    fields=[
                        {
                            "field_id": "registration_mode",
                            "value": "individual_or_household",
                            "evidence": "bản thân tôi",
                        }
                    ],
                )
            ]
        )
        extractor = StructuredExtractor(provider, self.catalog)

        outcome = extractor.extract(
            "Cho bản thân tôi.",
            context=ExtractionTurnContext(
                active_procedure_code="1.004194",
                expected_field_id="registration_mode",
            ),
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.fields["registration_mode"], "individual_or_household")
        envelope = json.loads(provider.calls[0].user_prompt)
        self.assertEqual(envelope["current_user_message"], "Cho bản thân tôi.")
        self.assertEqual(
            envelope["conversation_context"],
            {
                "active_procedure_code": "1.004194",
                "expected_field_id": "registration_mode",
                "confirmation_required": False,
                "recent_information_topics": [],
                "recent_information_procedure_code": None,
            },
        )
        self.assertNotIn("messages", envelope)

    def test_pending_confirmation_context_is_explicit_in_the_provider_envelope(self) -> None:
        provider = MockLLMProvider(
            [
                _payload(
                    procedure_code="1.004194",
                    fields=[
                        {
                            "field_id": "submission_channel",
                            "value": "online",
                            "evidence": "trực tuyến",
                        }
                    ],
                )
            ]
        )
        extractor = StructuredExtractor(provider, self.catalog)

        outcome = extractor.extract(
            "Đúng, tôi nộp trực tuyến",
            context=ExtractionTurnContext(
                "1.004194",
                confirmation_required=True,
            ),
        )

        self.assertTrue(outcome.succeeded)
        envelope = json.loads(provider.calls[0].user_prompt)
        self.assertEqual(
            envelope["conversation_context"],
            {
                "active_procedure_code": "1.004194",
                "expected_field_id": None,
                "confirmation_required": True,
                "recent_information_topics": [],
                "recent_information_procedure_code": None,
            },
        )

    def test_informational_request_routes_topics_and_grounded_enum_references(self) -> None:
        message = "Đăng ký tạm trú theo danh sách cần giấy gì và phí bao nhiêu?"
        provider = MockLLMProvider(
            [
                _payload(
                    classification="informational",
                    procedure_code="1.004194",
                    information_request={
                        "topics": ["documents", "fee"],
                        "target_field_id": None,
                        "reference_fields": [
                            {
                                "field_id": "registration_mode",
                                "value": "by_list",
                                "evidence": "theo danh sách",
                            }
                        ],
                    },
                )
            ]
        )

        outcome = StructuredExtractor(provider, self.catalog).extract(message)

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.classification, "informational")
        self.assertEqual(outcome.procedure_code, "1.004194")
        self.assertEqual(dict(outcome.fields), {})
        self.assertEqual(dict(outcome.context_signals), {})
        self.assertIsInstance(outcome.information_request, InformationRequest)
        assert outcome.information_request is not None
        self.assertEqual(
            outcome.information_request.topics,
            (QATopic.DOCUMENTS, QATopic.FEE),
        )
        self.assertEqual(
            dict(outcome.information_request.reference_fields),
            {"registration_mode": "by_list"},
        )
        self.assertEqual(
            dict(outcome.information_request.evidence),
            {"registration_mode": "theo danh sách"},
        )
        with self.assertRaises(TypeError):
            outcome.information_request.reference_fields["registration_mode"] = "x"  # type: ignore[index]

    def test_field_help_question_is_distinct_from_plain_enum_answer(self) -> None:
        question_provider = MockLLMProvider(
            [
                _payload(
                    classification="informational",
                    procedure_code="1.004194",
                    information_request={
                        "topics": ["field_help"],
                        "target_field_id": "registration_mode",
                        "reference_fields": [
                            {
                                "field_id": "registration_mode",
                                "value": "by_list",
                                "evidence": "theo danh sách",
                            }
                        ],
                    },
                )
            ]
        )
        answer_provider = MockLLMProvider(
            [
                _payload(
                    procedure_code="1.004194",
                    fields=[
                        {
                            "field_id": "registration_mode",
                            "value": "by_list",
                            "evidence": "theo danh sách",
                        }
                    ],
                )
            ]
        )
        context = ExtractionTurnContext("1.004194", "registration_mode")

        question = StructuredExtractor(question_provider, self.catalog).extract(
            "Theo danh sách tức là gì?", context=context
        )
        answer = StructuredExtractor(answer_provider, self.catalog).extract(
            "Theo danh sách", context=context
        )

        self.assertEqual(question.classification, "informational")
        assert question.information_request is not None
        self.assertEqual(question.information_request.target_field_id, "registration_mode")
        self.assertEqual(answer.classification, "supported")
        self.assertEqual(answer.fields["registration_mode"], "by_list")
        self.assertIsNone(answer.information_request)

    def test_unscoped_information_request_keeps_field_references_empty(self) -> None:
        provider = MockLLMProvider(
            [
                _payload(
                    classification="informational",
                    procedure_code=None,
                    information_request={
                        "topics": ["fee"],
                        "target_field_id": None,
                        "reference_fields": [],
                    },
                )
            ]
        )

        outcome = StructuredExtractor(provider, self.catalog).extract("Phí bao nhiêu?")

        self.assertTrue(outcome.succeeded)
        self.assertIsNone(outcome.procedure_code)
        assert outcome.information_request is not None
        self.assertEqual(outcome.information_request.topics, (QATopic.FEE,))

    def test_recent_information_topics_are_bounded_context_not_evidence(self) -> None:
        provider = MockLLMProvider(
            [
                _payload(
                    classification="informational",
                    procedure_code="2.000635",
                    information_request={
                        "topics": ["fee"],
                        "target_field_id": None,
                        "reference_fields": [
                            {
                                "field_id": "submission_channel",
                                "value": "direct",
                                "evidence": "trực tiếp",
                            }
                        ],
                    },
                )
            ]
        )
        context = ExtractionTurnContext(
            "1.004194",
            recent_information_topics=(QATopic.FEE,),
            recent_information_procedure_code="2.000635",
        )

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Còn trực tiếp thì sao?", context=context
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.procedure_code, "2.000635")
        envelope = json.loads(provider.calls[0].user_prompt)
        self.assertEqual(envelope["conversation_context"]["recent_information_topics"], ["fee"])
        self.assertEqual(
            envelope["conversation_context"]["recent_information_procedure_code"],
            "2.000635",
        )
        assert outcome.information_request is not None
        self.assertEqual(
            dict(outcome.information_request.reference_fields),
            {"submission_channel": "direct"},
        )

    def test_information_request_rejects_unsafe_shapes_and_ungrounded_references(self) -> None:
        cases = (
            _payload(
                classification="informational",
                procedure_code="1.004194",
                information_request={
                    "topics": [],
                    "target_field_id": None,
                    "reference_fields": [],
                },
            ),
            _payload(
                classification="informational",
                procedure_code="1.004194",
                information_request={
                    "topics": ["fee", "fee"],
                    "target_field_id": None,
                    "reference_fields": [],
                },
            ),
            _payload(
                classification="informational",
                procedure_code="1.004194",
                information_request={
                    "topics": ["fee", "documents", "steps", "authority"],
                    "target_field_id": None,
                    "reference_fields": [],
                },
            ),
            _payload(
                classification="informational",
                procedure_code="1.004194",
                information_request={
                    "topics": ["unknown_topic"],
                    "target_field_id": None,
                    "reference_fields": [],
                },
            ),
            _payload(
                classification="informational",
                procedure_code="1.004194",
                information_request=None,
            ),
            _payload(
                classification="informational",
                procedure_code="1.004194",
                information_request={
                    "topics": ["fee"],
                    "target_field_id": "registration_mode",
                    "reference_fields": [],
                },
            ),
            _payload(
                classification="informational",
                procedure_code="1.004194",
                information_request={
                    "topics": ["field_help"],
                    "target_field_id": None,
                    "reference_fields": [],
                },
            ),
            _payload(
                classification="informational",
                procedure_code=None,
                information_request={
                    "topics": ["fee"],
                    "target_field_id": None,
                    "reference_fields": [
                        {
                            "field_id": "submission_channel",
                            "value": "direct",
                            "evidence": "trực tiếp",
                        }
                    ],
                },
            ),
            _payload(
                classification="informational",
                procedure_code="1.004194",
                information_request={
                    "topics": ["fee"],
                    "target_field_id": None,
                    "reference_fields": [
                        {
                            "field_id": "applicant_full_name",
                            "value": "Người Mẫu",
                            "evidence": "Người Mẫu",
                        }
                    ],
                },
            ),
            _payload(
                classification="informational",
                procedure_code="1.004194",
                information_request={
                    "topics": ["fee"],
                    "target_field_id": None,
                    "reference_fields": [
                        {
                            "field_id": "submission_channel",
                            "value": "direct",
                            "evidence": "trực tiếp",
                        }
                    ],
                },
            ),
            _payload(
                classification="informational",
                procedure_code="1.004194",
                fields=[
                    {
                        "field_id": "submission_channel",
                        "value": "direct",
                        "evidence": "trực tiếp",
                    }
                ],
                information_request={
                    "topics": ["fee"],
                    "target_field_id": None,
                    "reference_fields": [],
                },
            ),
            _payload(
                information_request={
                    "topics": ["fee"],
                    "target_field_id": None,
                    "reference_fields": [],
                }
            ),
        )
        messages = (
            "Phí đăng ký tạm trú là bao nhiêu?",
            "Phí đăng ký tạm trú là bao nhiêu?",
            "Phí đăng ký tạm trú là bao nhiêu?",
            "Phí đăng ký tạm trú là bao nhiêu?",
            "Phí đăng ký tạm trú là bao nhiêu?",
            "Phí đăng ký tạm trú là bao nhiêu?",
            "Hình thức đăng ký tạm trú là gì?",
            "Phí bao nhiêu nếu nộp trực tiếp?",
            "Phí đăng ký tạm trú của Người Mẫu?",
            "Phí đăng ký tạm trú là bao nhiêu?",
            "Phí bao nhiêu nếu nộp trực tiếp?",
            "Tôi muốn đăng ký tạm trú.",
        )
        for payload, message in zip(cases, messages, strict=True):
            with self.subTest(payload=payload):
                provider = MockLLMProvider([payload, payload])
                outcome = StructuredExtractor(provider, self.catalog).extract(message)
                self.assertFalse(outcome.succeeded)
                self.assertEqual(outcome.error_code, "malformed_output")

    def test_recent_information_topic_context_rejects_invalid_values(self) -> None:
        for topics in (
            cast(tuple[QATopic, ...], [QATopic.FEE]),
            (QATopic.FEE, QATopic.FEE),
            cast(tuple[QATopic, ...], ("fee",)),
            (QATopic.FEE, QATopic.DOCUMENTS, QATopic.CHANNELS, QATopic.RESULT),
        ):
            with (
                self.subTest(topics=topics),
                self.assertRaisesRegex(ValueError, "recent_information_topics"),
            ):
                ExtractionTurnContext("1.004194", recent_information_topics=topics)

    def test_information_references_reject_cross_procedure_and_duplicates(self) -> None:
        unsafe_cases = (
            (
                _payload(
                    classification="informational",
                    procedure_code="2.000635",
                    information_request={
                        "topics": ["fee"],
                        "target_field_id": None,
                        "reference_fields": [
                            {
                                "field_id": "registration_mode",
                                "value": "by_list",
                                "evidence": "theo danh sách",
                            }
                        ],
                    },
                ),
                "Phí bản sao giấy khai sinh theo danh sách là bao nhiêu?",
            ),
            (
                _payload(
                    classification="informational",
                    procedure_code="1.004194",
                    information_request={
                        "topics": ["fee"],
                        "target_field_id": None,
                        "reference_fields": [
                            {
                                "field_id": "submission_channel",
                                "value": "direct",
                                "evidence": "trực tiếp",
                            },
                            {
                                "field_id": "submission_channel",
                                "value": "direct",
                                "evidence": "trực tiếp",
                            },
                        ],
                    },
                ),
                "Nếu nộp trực tiếp thì phí bao nhiêu?",
            ),
        )

        for payload, message in unsafe_cases:
            with self.subTest(message=message):
                provider = MockLLMProvider([payload, payload])
                outcome = StructuredExtractor(provider, self.catalog).extract(message)
                self.assertFalse(outcome.succeeded)
                self.assertEqual(outcome.error_code, "malformed_output")

    def test_context_cannot_be_reused_as_field_evidence(self) -> None:
        unsafe = _payload(
            procedure_code="1.004194",
            fields=[
                {
                    "field_id": "registration_mode",
                    "value": "individual_or_household",
                    "evidence": "registration_mode",
                }
            ],
        )
        provider = MockLLMProvider([unsafe, unsafe])

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Cho bản thân tôi.",
            context=ExtractionTurnContext(
                active_procedure_code="1.004194",
                expected_field_id="registration_mode",
            ),
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(dict(outcome.fields), {})

    def test_active_context_allows_new_supported_intent_for_core_to_require_reset(self) -> None:
        new_procedure = _payload(
            procedure_code="2.000635",
            fields=[
                {
                    "field_id": "requester_type",
                    "value": "self",
                    "evidence": "bản thân tôi",
                }
            ],
        )
        provider = MockLLMProvider([new_procedure])

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Tôi muốn cấp bản sao khai sinh cho bản thân tôi.",
            context=ExtractionTurnContext(
                active_procedure_code="1.004194",
                expected_field_id="registration_mode",
            ),
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.procedure_code, "2.000635")
        self.assertEqual(dict(outcome.fields), {"requester_type": "self"})
        self.assertEqual(provider.remaining, 0)

    def test_invalid_context_falls_back_before_provider_call(self) -> None:
        provider = MockLLMProvider([_payload()])
        extractor = StructuredExtractor(provider, self.catalog)
        invalid_contexts = (
            ExtractionTurnContext(active_procedure_code="9.999999"),
            ExtractionTurnContext(
                active_procedure_code="1.004194",
                expected_field_id="copies_requested",
            ),
        )

        for context in invalid_contexts:
            with self.subTest(context=context):
                outcome = extractor.extract("Câu trả lời ngắn.", context=context)
                self.assertEqual(outcome.error_code, "invalid_context")
                self.assertEqual(outcome.attempts, 0)
        self.assertEqual(provider.calls, [])
        with self.assertRaises(ValueError):
            ExtractionTurnContext("1.004194", expected_field_id="")

    def test_extracts_only_reviewed_text_rule_context_signals(self) -> None:
        message = "Tôi mới nhập quốc tịch Việt Nam và muốn đăng ký tạm trú."
        provider = MockLLMProvider(
            [
                _payload(
                    procedure_code="1.004194",
                    context_signals=[
                        {
                            "input_id": "newly_naturalized_or_restored_citizenship",
                            "value": True,
                            "evidence": "mới nhập quốc tịch Việt Nam",
                        }
                    ],
                )
            ]
        )

        outcome = StructuredExtractor(provider, self.catalog).extract(message)

        self.assertTrue(outcome.succeeded)
        self.assertEqual(
            outcome.context_signals["newly_naturalized_or_restored_citizenship"],
            True,
        )
        self.assertEqual(
            outcome.context_origins["newly_naturalized_or_restored_citizenship"],
            "user_declaration",
        )

        birth_message = "Tôi muốn xin bản sao giấy khai sinh."
        birth_provider = MockLLMProvider(
            [
                _payload(
                    context_signals=[
                        {
                            "input_id": "intent",
                            "value": "birth_certificate_copy",
                            "evidence": "bản sao giấy khai sinh",
                        }
                    ]
                )
            ]
        )
        birth_outcome = StructuredExtractor(birth_provider, self.catalog).extract(birth_message)
        self.assertTrue(birth_outcome.succeeded)
        self.assertEqual(birth_outcome.context_signals["intent"], "birth_certificate_copy")
        self.assertEqual(birth_outcome.context_origins["intent"], "intent_extraction")

    def test_boolean_context_signal_checks_full_message_polarity(self) -> None:
        input_id = "newly_naturalized_or_restored_citizenship"
        unsafe_cases = (
            (
                "Tôi không mới nhập quốc tịch Việt Nam.",
                "Tôi không mới nhập quốc tịch Việt Nam.",
            ),
            (
                "Tôi không mới nhập quốc tịch Việt Nam.",
                "mới nhập quốc tịch Việt Nam",
            ),
            ("Tôi thích bóng đá.", "Tôi thích bóng đá."),
            ("Tôi đang ở Việt Nam.", "Tôi đang ở Việt Nam."),
        )
        for message, evidence in unsafe_cases:
            with self.subTest(message=message, evidence=evidence):
                payload = _payload(
                    procedure_code="1.004194",
                    context_signals=[{"input_id": input_id, "value": True, "evidence": evidence}],
                )
                provider = MockLLMProvider([payload, payload])
                outcome = StructuredExtractor(provider, self.catalog).extract(message)
                self.assertTrue(outcome.succeeded)
                self.assertEqual(dict(outcome.context_signals), {})
                self.assertEqual(len(provider.calls), 1)

        negative_payload = _payload(
            procedure_code="1.004194",
            context_signals=[
                {
                    "input_id": input_id,
                    "value": False,
                    "evidence": "không mới nhập quốc tịch Việt Nam",
                }
            ],
        )
        negative = StructuredExtractor(MockLLMProvider([negative_payload]), self.catalog).extract(
            "Tôi không mới nhập quốc tịch Việt Nam."
        )
        self.assertTrue(negative.succeeded)
        self.assertIs(negative.context_signals[input_id], False)

        unrelated_negation = _payload(
            procedure_code="1.004194",
            context_signals=[
                {
                    "input_id": input_id,
                    "value": False,
                    "evidence": ("Tôi không sống ở Hà Nội, tôi mới nhập quốc tịch Việt Nam."),
                }
            ],
        )
        wrong_polarity = StructuredExtractor(
            MockLLMProvider([unrelated_negation, unrelated_negation]), self.catalog
        ).extract("Tôi không sống ở Hà Nội, tôi mới nhập quốc tịch Việt Nam.")
        self.assertTrue(wrong_polarity.succeeded)
        self.assertEqual(dict(wrong_polarity.context_signals), {})

    def test_text_model_cannot_emit_document_or_cross_procedure_signals(self) -> None:
        unsafe_cases: tuple[tuple[str, dict[str, object], str], ...] = (
            (
                "1.004194",
                {
                    "input_id": "ct01_missing",
                    "value": True,
                    "evidence": "thiếu CT01",
                },
                "Tôi thiếu CT01.",
            ),
            (
                "1.004194",
                {
                    "input_id": "intent",
                    "value": "birth_certificate_copy",
                    "evidence": "bản sao khai sinh",
                },
                "Tôi cần bản sao khai sinh nhưng đang ở luồng tạm trú.",
            ),
        )
        for procedure_code, signal, message in unsafe_cases:
            with self.subTest(signal=signal):
                payload = _payload(
                    procedure_code=procedure_code,
                    context_signals=[signal],
                )
                provider = MockLLMProvider([payload, payload])
                outcome = StructuredExtractor(provider, self.catalog).extract(message)
                self.assertFalse(outcome.succeeded)
                self.assertEqual(outcome.error_code, "malformed_output")

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

    def test_rejects_cross_procedure_unknown_and_duplicate_fields(self) -> None:
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
        )
        messages = (
            "Tôi đăng ký tạm trú và cần 2 bản.",
            "Tôi cần x.",
            "Tôi đăng ký tạm trú online.",
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

    def test_unverifiable_field_is_dropped_without_losing_supported_intent(self) -> None:
        provider = MockLLMProvider(
            [
                _payload(
                    procedure_code="1.004194",
                    fields=[
                        {
                            "field_id": "submission_channel",
                            "value": "online",
                            "evidence": "online",
                        }
                    ],
                )
            ]
        )

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Tôi đăng ký tạm trú trực tiếp."
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.procedure_code, "1.004194")
        self.assertEqual(dict(outcome.fields), {})

    def test_bad_candidate_does_not_discard_a_grounded_candidate(self) -> None:
        provider = MockLLMProvider(
            [
                _payload(
                    fields=[
                        {
                            "field_id": "copies_requested",
                            "value": 2,
                            "evidence": "2 bản",
                        },
                        {
                            "field_id": "submission_channel",
                            "value": "online",
                            "evidence": "trực tuyến",
                        },
                    ]
                )
            ]
        )

        outcome = StructuredExtractor(provider, self.catalog).extract(
            "Tôi cần 2 bản và sẽ đến nhận trực tiếp."
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(dict(outcome.fields), {"copies_requested": 2})

    def test_duplicate_field_is_rejected_even_when_first_candidate_would_be_dropped(self) -> None:
        duplicated = _payload(
            fields=[
                {
                    "field_id": "submission_channel",
                    "value": "online",
                    "evidence": "không xuất hiện",
                },
                {
                    "field_id": "submission_channel",
                    "value": "direct",
                    "evidence": "trực tiếp",
                },
            ]
        )
        provider = MockLLMProvider([duplicated, duplicated])

        outcome = StructuredExtractor(provider, self.catalog).extract("Tôi nhận trực tiếp.")

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.error_code, "malformed_output")

    def test_safe_reply_is_propagated_and_invalid_reply_is_rejected(self) -> None:
        safe_reply = "Dạ, em đã hiểu yêu cầu của anh/chị ạ."
        outcome = StructuredExtractor(
            MockLLMProvider([_payload(reply=safe_reply)]), self.catalog
        ).extract("Tôi cần bản sao Giấy khai sinh.")

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.reply, safe_reply)

        invalid_payloads = (
            _payload(reply=""),
            _payload(reply="x" * 241),
            {**_payload(), "reply": 42},
        )
        for invalid in invalid_payloads:
            with self.subTest(reply=invalid["reply"]):
                rejected = StructuredExtractor(
                    MockLLMProvider([invalid, invalid]), self.catalog
                ).extract("Tôi cần bản sao Giấy khai sinh.")
                self.assertFalse(rejected.succeeded)
                self.assertEqual(rejected.error_code, "malformed_output")

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

    def test_inconsistent_string_value_is_soft_dropped(self) -> None:
        provider = MockLLMProvider(
            [
                _payload(
                    fields=[
                        {
                            "field_id": "subject_full_name",
                            "value": "A",
                            "evidence": "Trần An",
                        }
                    ]
                )
            ]
        )

        outcome = StructuredExtractor(provider, self.catalog).extract("Trần An")

        self.assertTrue(outcome.succeeded)
        self.assertEqual(dict(outcome.fields), {})

    def test_non_supported_output_cannot_smuggle_fields_or_a_procedure(self) -> None:
        unsafe = _payload(
            classification="unsupported",
            procedure_code="2.000635",
            fields=[{"field_id": "copies_requested", "value": 1, "evidence": "1"}],
            context_signals=[
                {
                    "input_id": "intent",
                    "value": "birth_certificate_copy",
                    "evidence": "khai sinh",
                }
            ],
        )
        provider = MockLLMProvider([unsafe, unsafe])

        outcome = StructuredExtractor(provider, self.catalog).extract("Đăng ký khai sinh 1 bé.")

        self.assertFalse(outcome.succeeded)
        self.assertEqual(dict(outcome.fields), {})
        self.assertEqual(dict(outcome.context_signals), {})
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
        self.assertEqual(
            set(schema["properties"]["classification"]["enum"]),
            {"supported", "unsupported", "ambiguous", "informational"},
        )
        field_enum = schema["properties"]["fields"]["items"]["properties"]["field_id"]["enum"]
        expected_field_ids = {
            field.field_id for code in catalog.procedure_codes for field in catalog.fields_for(code)
        }
        self.assertEqual(set(field_enum), expected_field_ids)
        context_enum = schema["properties"]["context_signals"]["items"]["properties"]["input_id"][
            "enum"
        ]
        expected_context_ids = {
            item.input_id
            for code in catalog.procedure_codes
            for item in catalog.extractable_rule_contexts_for(code)
        }
        self.assertEqual(set(context_enum), expected_context_ids)
        information_schema = schema["properties"]["information_request"]
        self.assertEqual(
            set(information_schema["properties"]["topics"]["items"]["enum"]),
            {topic.value for topic in QATopic},
        )
        reference_enum = information_schema["properties"]["reference_fields"]["items"][
            "properties"
        ]["field_id"]["enum"]
        expected_enum_field_ids = {
            field.field_id
            for code in catalog.procedure_codes
            for field in catalog.fields_for(code)
            if field.field_type == "enum"
        }
        self.assertEqual(set(reference_enum), expected_enum_field_ids)
        self.assertNotIn("marriage_extract", json.dumps(schema))
        self.assertNotIn("death_extract", json.dumps(schema))
        schema_text = json.dumps(schema)
        self.assertLess(len(schema_text), 5_000)
        for unsupported_keyword in (
            '"format"',
            '"pattern"',
            '"minimum"',
            '"maximum"',
            '"maxLength"',
        ):
            self.assertNotIn(unsupported_keyword, schema_text)


if __name__ == "__main__":
    unittest.main()
