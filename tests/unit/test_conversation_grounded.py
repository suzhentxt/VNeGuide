from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest

from vneguide.ai import (
    ExtractionOutcome,
    ExtractionTurnContext,
    GroundedResponder,
    InformationRequest,
    MemoryCompactor,
    MockLLMProvider,
)
from vneguide.core import ConversationSession
from vneguide.data import ProcedureRepository
from vneguide.domain import NextAction, ProcedureCode, QATopic

ROOT = Path(__file__).resolve().parents[2]


class StubExtractor:
    def __init__(self, *outcomes: ExtractionOutcome) -> None:
        self.outcomes = deque(outcomes)

    def extract(
        self,
        message: str,
        *,
        context: ExtractionTurnContext | None = None,
    ) -> ExtractionOutcome:
        return self.outcomes.popleft()


def _outcome(
    *,
    classification: str = "supported",
    procedure_code: str | None = "2.000635",
    information_request: InformationRequest | None = None,
) -> ExtractionOutcome:
    return ExtractionOutcome(
        status="success",
        classification=classification,
        procedure_code=procedure_code,
        fields={},
        evidence={},
        clarification_question=None,
        attempts=1,
        reply=None,
        information_request=information_request,
    )


def _fallback_outcome(
    *,
    error_code: str = "invalid_value",
    invalid_field_id: str | None = "requester_personal_id",
) -> ExtractionOutcome:
    return ExtractionOutcome(
        status="fallback",
        classification=None,
        procedure_code=None,
        fields={},
        evidence={},
        clarification_question=None,
        attempts=1,
        reply=None,
        error_code=error_code,
        invalid_field_id=invalid_field_id,
    )


@pytest.fixture(scope="module")
def repository() -> ProcedureRepository:
    return ProcedureRepository.discover(ROOT)


def test_cold_start_greeting_uses_grounded_reply_not_out_of_scope(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(_outcome(classification="unsupported", procedure_code=None))
    provider = MockLLMProvider(
        [
            {
                "reply": "Dạ, em chào anh/chị ạ. Em hỗ trợ ba thủ tục: cấp bản sao giấy khai sinh, "
                "xác nhận điều kiện nhà ở và đăng ký tạm trú ạ.",
                "off_domain": False,
            }
        ]
    )
    responder = GroundedResponder(provider, repository)
    session = ConversationSession(extractor, repository, responder=responder)

    result = session.send("xin chào bạn")

    assert "nằm ngoài ba thủ tục" not in result.reply
    assert "chào" in result.reply.lower()
    assert result.next_action is NextAction.PRESENT_GUIDANCE


def test_cold_start_off_domain_keeps_out_of_scope_action(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(_outcome(classification="unsupported", procedure_code=None))
    provider = MockLLMProvider(
        [{"reply": "Dạ, em chưa hỗ trợ chủ đề thời tiết ạ.", "off_domain": True}]
    )
    responder = GroundedResponder(provider, repository)
    session = ConversationSession(extractor, repository, responder=responder)

    result = session.send("thời tiết hôm nay thế nào")

    assert result.next_action is NextAction.OUT_OF_SCOPE


def test_informational_uses_grounded_reply(repository: ProcedureRepository) -> None:
    request = InformationRequest((QATopic.REQUIRED_INFORMATION,))
    extractor = StubExtractor(
        _outcome(
            classification="informational",
            procedure_code=ProcedureCode.BIRTH_CERTIFICATE_COPY.value,
            information_request=request,
        )
    )
    provider = MockLLMProvider(
        [
            {
                "reply": "Dạ, anh/chị cần cung cấp họ tên, số định danh và kênh nộp ạ.",
                "off_domain": False,
            }
        ]
    )
    responder = GroundedResponder(provider, repository)
    session = ConversationSession(extractor, repository, responder=responder)

    result = session.send("giấy khai sinh cần những thông tin nào")

    assert result.source_ids
    assert result.next_action is NextAction.PRESENT_GUIDANCE
    assert "Đúng" not in result.reply


def test_greeting_falls_back_to_deterministic_when_provider_fails(
    repository: ProcedureRepository,
) -> None:
    from vneguide.ai import ProviderError

    extractor = StubExtractor(_outcome(classification="unsupported", procedure_code=None))
    provider = MockLLMProvider([ProviderError("gateway down", retryable=True)])
    responder = GroundedResponder(provider, repository)
    session = ConversationSession(extractor, repository, responder=responder)

    result = session.send("xin chào bạn")

    assert result.next_action is NextAction.OUT_OF_SCOPE


def test_no_responder_preserves_old_deterministic_behavior(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(_outcome(classification="unsupported", procedure_code=None))
    session = ConversationSession(extractor, repository)

    result = session.send("xin chào bạn")

    assert "nằm ngoài ba thủ tục" in result.reply
    assert result.next_action is NextAction.OUT_OF_SCOPE


def test_invalid_value_fallback_gives_field_specific_correction(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(_fallback_outcome(invalid_field_id="requester_personal_id"))
    session = ConversationSession(extractor, repository)
    session.initialize_procedure("2.000635")

    result = session.send("số định danh là 01239501239")

    assert "chưa đúng định dạng" in result.reply
    assert "Số định danh cá nhân" in result.reply
    assert result.next_action is NextAction.RETRY


def test_invalid_value_without_field_id_keeps_generic_fallback(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(_fallback_outcome(invalid_field_id=None))
    session = ConversationSession(extractor, repository)
    session.initialize_procedure("2.000635")

    result = session.send("số định danh là 01239501239")

    assert "chưa nghe rõ" in result.reply
    assert result.next_action is NextAction.RETRY


def test_conversation_history_is_threaded_to_responder_for_recall(
    repository: ProcedureRepository,
) -> None:
    extractor = StubExtractor(
        _outcome(classification="unsupported", procedure_code=None),
        _outcome(classification="unsupported", procedure_code=None),
    )
    provider = MockLLMProvider(
        [
            {"reply": "Dạ, em chào anh Hậu ạ.", "off_domain": False},
            {"reply": "Dạ, anh tên là Hậu ạ.", "off_domain": False},
        ]
    )
    responder = GroundedResponder(provider, repository)
    session = ConversationSession(extractor, repository, responder=responder)

    session.send("tôi tên Hậu")
    session.send("tôi tên là gì")

    second_prompt = provider.calls[1].system_prompt
    assert "tôi tên Hậu" in second_prompt
    assert "Công dân" in second_prompt


def test_compaction_triggers_and_feeds_summary_to_responder(
    repository: ProcedureRepository,
) -> None:
    outcomes = tuple(_outcome(classification="unsupported", procedure_code=None) for _ in range(8))
    extractor = StubExtractor(*outcomes)
    replies: list[object] = [
        {"reply": f"Dạ, em ghi nhận lượt {i} ạ.", "off_domain": False} for i in range(7)
    ]
    replies.append({"summary": "Công dân tên Hậu, đang social talk."})
    replies.append({"reply": "Dạ, anh tên là Hậu ạ.", "off_domain": False})
    provider = MockLLMProvider(replies)
    responder = GroundedResponder(provider, repository)
    compactor = MemoryCompactor(provider)
    session = ConversationSession(extractor, repository, responder=responder, compactor=compactor)

    session.send("tôi tên Hậu")
    for i in range(6):
        session.send(f"lượt phụ {i}")
    assert session.state.memory_summary == "Công dân tên Hậu, đang social talk."
    assert len(session.state.messages) == 6

    session.send("tôi tên là gì")

    final_prompt = provider.calls[-1].system_prompt
    assert "Công dân tên Hậu" in final_prompt
    assert "Tóm tắt hội thoại trước đó" in final_prompt


def test_compaction_failure_leaves_messages_intact(
    repository: ProcedureRepository,
) -> None:
    from vneguide.ai import ProviderError

    outcomes = tuple(_outcome(classification="unsupported", procedure_code=None) for _ in range(7))
    extractor = StubExtractor(*outcomes)
    replies: list[object] = [{"reply": f"Dạ, lượt {i} ạ.", "off_domain": False} for i in range(7)]
    replies.append(ProviderError("gateway down", retryable=True))
    provider = MockLLMProvider(replies)
    responder = GroundedResponder(provider, repository)
    compactor = MemoryCompactor(provider)
    session = ConversationSession(extractor, repository, responder=responder, compactor=compactor)

    for i in range(7):
        session.send(f"lượt {i}")

    assert session.state.memory_summary == ""
    assert len(session.state.messages) == 14
