from __future__ import annotations

from collections import deque

import pytest
from httpx import ASGITransport, AsyncClient

from vneguide.ai import ExtractionOutcome, ExtractionTurnContext
from vneguide.api import create_app
from vneguide.core import CatalogReplyComposer, ConversationSession
from vneguide.data import ProcedureRepository
from vneguide.domain import (
    CaseDraft,
    ChatMessage,
    ConversationState,
    JSONValue,
    MessageRole,
    NextAction,
    ProcedureCode,
    TurnResult,
)


class FakeChatSession:
    def __init__(self) -> None:
        self._state = ConversationState()

    @property
    def state(self) -> ConversationState:
        return self._state

    def initialize_procedure(self, procedure_code: ProcedureCode | str) -> None:
        self._state = ConversationState(
            draft=CaseDraft(
                procedure_code=ProcedureCode(procedure_code),
                pack_version="test",
            )
        )

    def send(self, message: str) -> TurnResult:
        self._state = ConversationState(
            messages=(
                ChatMessage(MessageRole.USER, message),
                ChatMessage(MessageRole.ASSISTANT, "Bạn cần thực hiện thủ tục cụ thể nào?"),
            ),
            turn_number=1,
        )
        return TurnResult(
            reply="Bạn cần thực hiện thủ tục cụ thể nào?",
            state=self._state,
            next_action=NextAction.ASK_CLARIFICATION,
        )

    def accept_suggestion(self, _suggestion_id: str, *, expected_revision: int) -> TurnResult:
        raise ValueError("no suggestion")

    def reject_suggestion(self, _suggestion_id: str, *, expected_revision: int) -> TurnResult:
        raise ValueError("no suggestion")

    def edit_suggestion(
        self,
        _suggestion_id: str,
        _value: JSONValue,
        *,
        expected_revision: int,
    ) -> TurnResult:
        raise ValueError("no suggestion")

    def edit_field(
        self,
        _field_id: str,
        _value: JSONValue,
        *,
        expected_revision: int,
    ) -> TurnResult:
        raise ValueError("no suggestion")

    def close(self) -> None:
        self._state = ConversationState()


class StubExtractor:
    def __init__(self, *outcomes: ExtractionOutcome) -> None:
        self._outcomes = deque(outcomes)
        self.calls: list[tuple[str, ExtractionTurnContext | None]] = []

    def extract(
        self,
        message: str,
        *,
        context: ExtractionTurnContext | None = None,
    ) -> ExtractionOutcome:
        self.calls.append((message, context))
        return self._outcomes.popleft()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_chat_api_creates_session_and_sends_message() -> None:
    app = create_app(
        session_factory=FakeChatSession,
        repository=ProcedureRepository.discover(),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/v1/chat/sessions",
            json={
                "context": {
                    "procedure_code": "1.000894",
                    "procedure_title": "Đăng ký kết hôn",
                    "route": "/hon-nhan-va-gia-dinh/dang-ky-ket-hon",
                }
            },
        )

        assert created.status_code == 201
        assert created.json()["context_supported"] is False
        assert created.json()["scope_warning"]
        session_id = created.headers["X-VNeGuide-Session"]

        turn = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": "Tôi cần hỗ trợ", "client_turn_id": "turn-1"},
        )
        repeated = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": "Tin nhắn gửi lại", "client_turn_id": "turn-1"},
        )

    assert turn.status_code == 200
    assert repeated.json() == turn.json()
    assert turn.json()["next_action"] == "ask_clarification"
    assert [message["role"] for message in turn.json()["messages"]] == [
        "user",
        "assistant",
    ]


@pytest.mark.anyio
async def test_chat_api_returns_stable_missing_session_error() -> None:
    app = create_app(
        session_factory=FakeChatSession,
        repository=ProcedureRepository.discover(),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/chat/sessions/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "session_not_found",
            "message": "Không tìm thấy phiên trò chuyện.",
            "retryable": False,
        }
    }


@pytest.mark.anyio
async def test_chat_api_accepts_a_pending_suggestion() -> None:
    repository = ProcedureRepository.discover()

    def session_factory() -> ConversationSession:
        return ConversationSession(
            StubExtractor(
                ExtractionOutcome(
                    status="success",
                    classification="supported",
                    procedure_code="2.000635",
                    fields={"copies_requested": 2},
                    evidence={"copies_requested": "xin 2 bản"},
                    clarification_question=None,
                    attempts=1,
                    error_code=None,
                )
            ),
            repository,
        )

    app = create_app(session_factory=session_factory, repository=repository)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/v1/chat/sessions", json={})
        session_id = created.headers["X-VNeGuide-Session"]
        turn = (
            await client.post(
                f"/v1/chat/sessions/{session_id}/messages",
                json={"message": "Tôi muốn xin 2 bản"},
            )
        ).json()
        suggestion = turn["suggestions"][0]

        accepted = await client.post(
            f"/v1/chat/sessions/{session_id}/suggestions/{suggestion['id']}",
            json={"action": "accept", "expected_revision": suggestion["revision"]},
        )
        stale = await client.post(
            f"/v1/chat/sessions/{session_id}/suggestions/{suggestion['id']}",
            json={"action": "accept", "expected_revision": suggestion["revision"]},
        )

    assert accepted.status_code == 200
    assert accepted.json()["draft"]["revision"] == 1
    assert accepted.json()["suggestions"][0]["status"] == "accepted"
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_suggestion"


@pytest.mark.anyio
async def test_chat_api_presents_grounded_guidance_without_mutating_draft() -> None:
    repository = ProcedureRepository.discover()

    def session_factory() -> ConversationSession:
        return ConversationSession(
            StubExtractor(
                ExtractionOutcome(
                    status="success",
                    classification="supported",
                    procedure_code="1.004194",
                    fields={},
                    evidence={},
                    clarification_question=None,
                    attempts=1,
                )
            ),
            repository,
            reply_composer=CatalogReplyComposer(repository),
        )

    app = create_app(session_factory=session_factory, repository=repository)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/v1/chat/sessions", json={})
        session_id = created.headers["X-VNeGuide-Session"]
        turn = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": "Lệ phí bao nhiêu?"},
        )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["next_action"] == "present_guidance"
    assert "7.000 đồng" in payload["reply"]
    assert payload["draft"]["values"] == {}
    assert payload["draft"]["revision"] == 0
    assert {source["id"] for source in payload["sources"]} <= set(
        repository.get_by_code("1.004194").source_ids
    )


@pytest.mark.anyio
async def test_chat_api_keeps_compact_memory_across_multiple_turns() -> None:
    repository = ProcedureRepository.discover()
    extractor = StubExtractor(
        ExtractionOutcome(
            status="success",
            classification="supported",
            procedure_code="1.004194",
            fields={},
            evidence={},
            clarification_question=None,
            attempts=1,
        ),
        ExtractionOutcome(
            status="success",
            classification="unsupported",
            procedure_code=None,
            fields={},
            evidence={},
            clarification_question=None,
            attempts=1,
        ),
        ExtractionOutcome(
            status="success",
            classification="supported",
            procedure_code="1.004194",
            fields={"submission_channel": "online"},
            evidence={"submission_channel": "trực tuyến"},
            clarification_question=None,
            attempts=1,
        ),
    )

    app = create_app(
        session_factory=lambda: ConversationSession(extractor, repository),
        repository=repository,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/v1/chat/sessions", json={})
        session_id = created.headers["X-VNeGuide-Session"]
        first = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": "Tôi muốn đăng ký tạm trú"},
        )
        off_topic = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": "Bạn ăn cơm chưa?"},
        )
        continued = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": "Tôi đăng ký trực tuyến"},
        )

    assert first.status_code == 200
    assert off_topic.json()["next_action"] == "out_of_scope"
    assert continued.status_code == 200
    assert continued.json()["procedure"]["code"] == "1.004194"
    assert continued.json()["next_action"] == "confirm_suggestion"
    assert continued.json()["suggestions"][-1]["field_id"] == "submission_channel"
    assert [call[1] for call in extractor.calls] == [
        None,
        ExtractionTurnContext("1.004194", "registration_mode"),
        ExtractionTurnContext("1.004194", "registration_mode"),
    ]
