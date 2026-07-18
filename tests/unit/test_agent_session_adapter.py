"""Tests for the DeepAgentSession adapter (Phase 2/3).

Verifies that the deep agent re-composes informational replies using grounded
tools, that source_ids are propagated from tool results, and that the
suggestion lifecycle still delegates to the ConversationSession base.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from vneguide.agent.session_adapter import DeepAgentSession
from vneguide.ai import (
    ExtractionOutcome,
    GroundedResponder,
    InformationRequest,
    MemoryCompactor,
    MockLLMProvider,
)
from vneguide.ai.providers.fake_chat import FakeChatModel
from vneguide.core.session import ConversationSession
from vneguide.data import ProcedureRepository
from vneguide.domain import NextAction, QATopic

ROOT = Path(__file__).resolve().parents[2]


class StubExtractor:
    def __init__(self, *outcomes: ExtractionOutcome) -> None:
        self.outcomes = deque(outcomes)

    def extract(self, message: str, *, context: object = None) -> ExtractionOutcome:
        return self.outcomes.popleft()


def _informational_outcome(
    code: str = "1.004194",
    topic: QATopic = QATopic.FEE,
) -> ExtractionOutcome:
    return ExtractionOutcome(
        status="success",
        classification="informational",
        procedure_code=code,
        fields={},
        evidence={},
        clarification_question=None,
        attempts=1,
        reply=None,
        information_request=InformationRequest(topics=(topic,)),
    )


def _make_session(
    model: FakeChatModel,
    extractor: StubExtractor,
    repository: ProcedureRepository,
) -> DeepAgentSession:
    return DeepAgentSession(
        model,
        extractor,
        repository,
        responder=GroundedResponder(MockLLMProvider(), repository),
        compactor=MemoryCompactor(MockLLMProvider()),
    )


@pytest.fixture(scope="module")
def repository() -> ProcedureRepository:
    return ProcedureRepository.discover(ROOT)


def test_deep_agent_session_is_conversation_session(repository: ProcedureRepository) -> None:
    model = FakeChatModel(responses=[])
    session = _make_session(model, StubExtractor(), repository)
    assert isinstance(session, ConversationSession)
    session.close()


def test_informational_reply_recomposed_by_agent(repository: ProcedureRepository) -> None:
    model = FakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_procedure_fee",
                        "args": {"procedure_code": "1.004194"},
                        "id": "1",
                    }
                ],
            ),
            AIMessage(
                content="Dạ, lệ phí đăng ký tạm trú là 7.000đ trực tuyến, 15.000đ trực tiếp ạ."
            ),
        ]
    )
    extractor = StubExtractor(_informational_outcome())
    session = _make_session(model, extractor, repository)
    result = session.send("Đăng ký tạm trú mất bao nhiêu tiền?")
    assert "7.000đ" in result.reply or "7.000" in result.reply
    assert result.next_action is NextAction.CONFIRM_PROCEDURE
    assert len(result.source_ids) > 0
    session.close()


def test_source_ids_propagated_from_tool_results(repository: ProcedureRepository) -> None:
    model = FakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_legal_basis",
                        "args": {"procedure_code": "1.004194"},
                        "id": "1",
                    }
                ],
            ),
            AIMessage(content="Căn cứ pháp lý của thủ tục tạm trú là..."),
        ]
    )
    extractor = StubExtractor(_informational_outcome(topic=QATopic.LEGAL_BASIS))
    session = _make_session(model, extractor, repository)
    result = session.send("Căn cứ pháp lý của đăng ký tạm trú là gì?")
    assert result.source_ids
    assert any(sid.startswith("SRC-") for sid in result.source_ids)
    session.close()


def test_agent_failure_falls_back_to_delegate(repository: ProcedureRepository) -> None:
    model = FakeChatModel(responses=[])
    extractor = StubExtractor(_informational_outcome())
    session = _make_session(model, extractor, repository)
    result = session.send("Đăng ký tạm trú mất bao nhiêu tiền?")
    assert result.reply
    assert result.next_action is NextAction.CONFIRM_PROCEDURE
    session.close()


def test_extractor_failure_keeps_core_fallback_without_agent_rewrite(
    repository: ProcedureRepository,
) -> None:
    fallback = ExtractionOutcome(
        status="fallback",
        classification=None,
        procedure_code=None,
        fields={},
        evidence={},
        clarification_question=None,
        attempts=1,
        error_code="malformed_output",
    )
    model = FakeChatModel(responses=["Nội dung không được dùng."])
    session = _make_session(model, StubExtractor(fallback), repository)
    session.initialize_procedure("1.004194")

    result = session.send("Thông tin tổng hợp.")

    assert "nói lại" in result.reply
    assert model.remaining == 1
    session.close()


def test_non_informational_skips_agent(repository: ProcedureRepository) -> None:
    supported_outcome = ExtractionOutcome(
        status="success",
        classification="unsupported",
        procedure_code=None,
        fields={},
        evidence={},
        clarification_question=None,
        attempts=1,
        reply=None,
    )
    model = FakeChatModel(responses=[])
    extractor = StubExtractor(supported_outcome)
    session = _make_session(model, extractor, repository)
    result = session.send("Tôi muốn đăng ký kết hôn")
    assert result.next_action is not NextAction.PRESENT_GUIDANCE
    assert model.remaining == 0
    session.close()
