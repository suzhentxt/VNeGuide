from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from vneguide.ai import ExtractionCatalog, MockLLMProvider, StructuredExtractor
from vneguide.core import ConversationSession
from vneguide.data import ProcedureRepository
from vneguide.domain import NextAction, ProcedureCode
from vneguide.language import (
    InputSource,
    LanguageNormalizer,
    ModelNormalizationCandidate,
    ModelNormalizationUnavailable,
    ProtectedKind,
    ProviderModelNormalizer,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    (
        ("tui muốn làm tạm chú", "tôi muốn đăng ký tạm trú"),
        ("Tui ưng mần tạm trú", "Tôi muốn đăng ký tạm trú"),
        ("hộ khẩu photo có được hông", "bản sao sổ hộ khẩu có được không"),
        ("Chừ tôi nỏ biết ở mô", "Bây giờ tôi không biết ở đâu"),
        ("Tôi muốn xin bảo sao khai sanh", "Tôi muốn xin bản sao khai sinh"),
    ),
)
def test_reviewed_dialect_and_asr_rules_are_deterministic(
    raw_text: str,
    expected: str,
) -> None:
    result = LanguageNormalizer().normalize(raw_text)

    assert result.normalized_text == expected
    assert result.changed_spans
    assert not result.model_assisted


def test_every_identity_bearing_span_is_preserved() -> None:
    raw_text = (
        "tui tên Trần Văn Tám, CCCD 012345678901, sinh ngày 07/08/1970, "
        "ở tại ấp Bển; số 0901234567; mã thủ tục 1.004194; hồ sơ HS-TUI-001"
    )

    result = LanguageNormalizer().normalize(raw_text)

    expected = {
        ProtectedKind.FULL_NAME: "Trần Văn Tám",
        ProtectedKind.CCCD: "012345678901",
        ProtectedKind.DATE_OF_BIRTH: "07/08/1970",
        ProtectedKind.ADDRESS: "ấp Bển",
        ProtectedKind.PROCEDURE_CODE: "1.004194",
        ProtectedKind.PHONE_NUMBER: "0901234567",
        ProtectedKind.CASE_CODE: "HS-TUI-001",
    }
    assert {span.kind: span.value for span in result.protected_spans} == expected
    assert all(result.normalized_text.count(value) == 1 for value in expected.values())
    assert "ấp Bển" in result.normalized_text
    assert "HS-TUI-001" in result.normalized_text


def test_normalized_evidence_maps_back_to_raw_user_words() -> None:
    result = LanguageNormalizer().normalize("tui muốn làm tạm chú")

    assert result.raw_text_for("tôi") == "tui"
    assert result.raw_text_for("đăng ký tạm trú") == "làm tạm chú"
    assert result.raw_text_for("tôi muốn đăng ký tạm trú") == "tui muốn làm tạm chú"


@dataclass
class _RecordingModelNormalizer:
    response: ModelNormalizationCandidate
    calls: list[str] = field(default_factory=list)

    def normalize(self, protected_text: str) -> ModelNormalizationCandidate:
        self.calls.append(protected_text)
        return self.response


def test_known_ambiguity_is_not_sent_to_model_or_inferred() -> None:
    model = _RecordingModelNormalizer(ModelNormalizationCandidate("ignored", 1.0))

    result = LanguageNormalizer(model_normalizer=model).normalize("Tôi cần giấy nhà")

    assert model.calls == []
    assert result.normalized_text == "Tôi cần giấy nhà"
    assert result.clarification_prompt() == (
        "Bạn nói “giấy nhà”. Bạn đang muốn hỏi: "
        "[Giấy chứng nhận quyền sử dụng đất]; [Giấy xác nhận chỗ ở]; [Khác]"
    )


@pytest.mark.parametrize("source", (InputSource.TEXT, InputSource.SPEECH))
def test_optional_model_tier_supports_text_and_speech_without_exposing_name(
    source: InputSource,
) -> None:
    model = _RecordingModelNormalizer(
        ModelNormalizationCandidate(
            "tôi tên ⟦PROTECTED_0⟧ muốn đăng ký tạm trú",
            0.91,
        )
    )

    result = LanguageNormalizer(model_normalizer=model).normalize(
        "tôi tên Nguyễn Thị Bảy muốn đăng kí tạm chứ",
        source=source,
    )

    assert model.calls == ["tôi tên ⟦PROTECTED_0⟧ muốn đăng kí tạm chứ"]
    assert "Nguyễn Thị Bảy" not in model.calls[0]
    assert result.normalized_text == "tôi tên Nguyễn Thị Bảy muốn đăng ký tạm trú"
    assert result.model_assisted


class _UnavailableModelNormalizer:
    def normalize(self, protected_text: str) -> ModelNormalizationCandidate:
        raise ModelNormalizationUnavailable("synthetic failure")


def test_model_failure_falls_back_without_changing_input() -> None:
    result = LanguageNormalizer(model_normalizer=_UnavailableModelNormalizer()).normalize(
        "một câu chưa có trong từ điển",
        source=InputSource.SPEECH,
    )

    assert result.normalized_text == "một câu chưa có trong từ điển"
    assert not result.model_assisted


def test_provider_model_tier_requires_every_change_to_be_declared() -> None:
    valid_provider = MockLLMProvider(
        [
            {
                "normalized_text": "tạm trú",
                "changed_spans": [
                    {
                        "start": 0,
                        "end": 7,
                        "original": "tạm chứ",
                        "normalized": "tạm trú",
                    }
                ],
                "confidence": 0.92,
                "ambiguities": [],
            }
        ]
    )
    candidate = ProviderModelNormalizer(valid_provider).normalize("tạm chứ")

    assert candidate.normalized_text == "tạm trú"
    assert valid_provider.calls[0].schema_name == "vneguide_language_normalization"
    assert "phương ngữ" in valid_provider.calls[0].system_prompt

    hidden_inference_provider = MockLLMProvider(
        [
            {
                "normalized_text": "tạm trú trực tuyến",
                "changed_spans": [
                    {
                        "start": 0,
                        "end": 7,
                        "original": "tạm chứ",
                        "normalized": "tạm trú",
                    }
                ],
                "confidence": 0.92,
                "ambiguities": [],
            }
        ]
    )

    with pytest.raises(ModelNormalizationUnavailable, match="outside declared spans"):
        ProviderModelNormalizer(hidden_inference_provider).normalize("tạm chứ")


@pytest.mark.xfail(
    reason="Session-level alias routing was removed in the deepagents refactor; "
    "dialect routing now relies on the LLM extractor instead of regex helpers.",
    strict=True,
)
def test_conversation_shows_grounded_language_ambiguity_options() -> None:
    repository = ProcedureRepository.discover(ROOT)
    catalog = ExtractionCatalog.from_data_package(ROOT / "data")
    session = ConversationSession(
        StructuredExtractor(MockLLMProvider([]), catalog),
        repository,
    )

    result = session.send("Tôi cần giấy nhà")

    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "Bạn nói “giấy nhà”" in result.reply
    assert "Giấy xác nhận chỗ ở" in result.reply


@pytest.mark.xfail(
    reason="Session-level alias routing was removed in the deepagents refactor; "
    "dialect routing now relies on the LLM extractor instead of regex helpers.",
    strict=True,
)
def test_reviewed_route_alias_uses_normalized_message_and_calls_provider() -> None:
    repository = ProcedureRepository.discover(ROOT)
    catalog = ExtractionCatalog.from_data_package(ROOT / "data")
    provider = MockLLMProvider(
        [
            {
                "classification": "unsupported",
                "procedure_code": None,
                "clarification_question": None,
                "fields": [],
                "context_signals": [],
            }
        ]
    )
    session = ConversationSession(StructuredExtractor(provider, catalog), repository)

    result = session.send("Tui ưng mần tạm trú")

    assert result.state.draft.procedure_code is ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION
    assert result.next_action is NextAction.ASK_CLARIFICATION
    assert "đúng không" in result.reply.lower()
    assert provider.remaining == 0
    assert len(provider.calls) == 1
