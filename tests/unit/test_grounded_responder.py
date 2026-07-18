from __future__ import annotations

from pathlib import Path

import pytest

from vneguide.ai import (
    GroundedResponder,
    InformationRequest,
    MockLLMProvider,
    ProviderError,
    ResponderContext,
)
from vneguide.data import ProcedureRepository
from vneguide.domain import ChatMessage, MessageRole, ProcedureCode, QATopic

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def repository() -> ProcedureRepository:
    return ProcedureRepository.discover(ROOT)


def _ctx(
    message: str,
    *,
    classification: str = "unsupported",
    procedure_code: str | None = None,
    information_request: InformationRequest | None = None,
    active: str | None = None,
    pending: str | None = None,
    recent_turns: tuple[ChatMessage, ...] = (),
) -> ResponderContext:
    return ResponderContext(
        user_message=message,
        classification=classification,
        procedure_code=procedure_code,
        information_request=information_request,
        active_procedure_code=active,
        pending_procedure_code=pending,
        filled_field_labels=(),
        missing_field_labels=(),
        draft_values={},
        recent_turns=recent_turns,
    )


def test_small_talk_returns_warm_reply_listing_procedures(
    repository: ProcedureRepository,
) -> None:
    provider = MockLLMProvider(
        [
            {
                "reply": "Dạ, em chào anh/chị ạ. Em hỗ trợ cấp bản sao giấy khai sinh, "
                "xác nhận điều kiện nhà ở và đăng ký tạm trú ạ.",
                "off_domain": False,
            }
        ]
    )
    responder = GroundedResponder(provider, repository)
    result = responder.respond(_ctx("xin chào bạn"))

    assert result.succeeded is True
    assert result.off_domain is False
    assert result.text is not None
    assert "chào" in result.text.lower()


def test_off_domain_topic_marked_off_domain(repository: ProcedureRepository) -> None:
    provider = MockLLMProvider(
        [
            {
                "reply": "Dạ, em chưa hỗ trợ chủ đề này ạ. Em có thể giúp ba thủ tục hành chính ạ.",
                "off_domain": True,
            }
        ]
    )
    responder = GroundedResponder(provider, repository)
    result = responder.respond(_ctx("thời tiết hôm nay thế nào"))

    assert result.succeeded is True
    assert result.off_domain is True


def test_informational_reply_is_grounded_in_reviewed_data(
    repository: ProcedureRepository,
) -> None:
    request = InformationRequest((QATopic.REQUIRED_INFORMATION,))
    provider = MockLLMProvider(
        [
            {
                "reply": (
                    "Dạ, để cấp bản sao giấy khai sinh, anh/chị cần cung cấp loại người yêu cầu, "
                    "họ tên, số định danh và kênh nộp ạ."
                ),
                "off_domain": False,
            }
        ]
    )
    responder = GroundedResponder(provider, repository)
    result = responder.respond(
        _ctx(
            "giấy khai sinh cần những thông tin nào",
            classification="informational",
            procedure_code=ProcedureCode.BIRTH_CERTIFICATE_COPY.value,
            information_request=request,
        )
    )

    assert result.succeeded is True
    assert result.source_ids
    call = provider.calls[0]
    assert "Thông tin đã duyệt" in call.system_prompt
    assert "thông tin cần khai" in call.system_prompt.lower()


def test_field_help_without_help_text_includes_format_hint(
    repository: ProcedureRepository,
) -> None:
    request = InformationRequest((QATopic.FIELD_HELP,), target_field_id="subject_date_of_birth")
    provider = MockLLMProvider(
        [{"reply": "Dạ, anh/chị nhập đầy đủ ngày/tháng/năm sinh ạ.", "off_domain": False}]
    )
    responder = GroundedResponder(provider, repository)
    result = responder.respond(
        _ctx(
            "ngày sinh là nêu ngày tháng năm sinh hay ngày thôi",
            classification="informational",
            procedure_code=ProcedureCode.BIRTH_CERTIFICATE_COPY.value,
            information_request=request,
        )
    )

    assert result.succeeded is True
    call = provider.calls[0]
    assert "ngày/tháng/năm" in call.system_prompt


def test_provider_failure_returns_succeeded_false_for_fallback(
    repository: ProcedureRepository,
) -> None:
    provider = MockLLMProvider([ProviderError("gateway down", retryable=True)])
    responder = GroundedResponder(provider, repository)
    result = responder.respond(_ctx("xin chào bạn"))

    assert result.succeeded is False
    assert result.text is None


def test_malformed_payload_returns_succeeded_false(
    repository: ProcedureRepository,
) -> None:
    provider = MockLLMProvider([{"reply": "", "off_domain": False}])
    responder = GroundedResponder(provider, repository)
    result = responder.respond(_ctx("xin chào bạn"))

    assert result.succeeded is False


def test_responder_context_validates_empty_message() -> None:
    with pytest.raises(ValueError):
        ResponderContext(
            user_message="   ",
            classification="unsupported",
            procedure_code=None,
            information_request=None,
            active_procedure_code=None,
            pending_procedure_code=None,
            filled_field_labels=(),
            missing_field_labels=(),
            draft_values={},
        )


def test_recent_turns_appear_in_prompt_for_recall(repository: ProcedureRepository) -> None:
    history = (
        ChatMessage(MessageRole.USER, "tôi tên Hậu"),
        ChatMessage(MessageRole.ASSISTANT, "Dạ, em chào anh Hậu ạ."),
    )
    provider = MockLLMProvider([{"reply": "Dạ, anh đã nói tên là Hậu ạ.", "off_domain": False}])
    responder = GroundedResponder(provider, repository)
    result = responder.respond(_ctx("Tôi tên là gì", recent_turns=history))

    assert result.succeeded is True
    call = provider.calls[0]
    assert "tôi tên Hậu" in call.system_prompt
    assert "Công dân" in call.system_prompt
    assert "Trợ lý" in call.system_prompt


def test_recent_turns_rejects_too_many_messages() -> None:
    too_many = tuple(ChatMessage(MessageRole.USER, f"lượt {i}") for i in range(7))
    with pytest.raises(ValueError):
        ResponderContext(
            user_message="ok",
            classification="unsupported",
            procedure_code=None,
            information_request=None,
            active_procedure_code=None,
            pending_procedure_code=None,
            filled_field_labels=(),
            missing_field_labels=(),
            draft_values={},
            recent_turns=too_many,
        )
