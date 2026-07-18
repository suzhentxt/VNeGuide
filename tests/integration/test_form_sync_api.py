from __future__ import annotations

from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient, Response

from vneguide.ai import ExtractionOutcome, ExtractionTurnContext
from vneguide.api import create_app
from vneguide.core import ConversationSession
from vneguide.data import ProcedureRepository

TEMPORARY_RESIDENCE_CODE = "1.004194"
TEMPORARY_ADDRESS = "Số 10 phố Tràng Thi, phường Hoàn Kiếm, Hà Nội"


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
        if not self._outcomes:
            raise AssertionError("Unexpected extractor call")
        return self._outcomes.popleft()


def _supported_context() -> dict[str, object]:
    return {
        "context": {
            "procedure_code": TEMPORARY_RESIDENCE_CODE,
            "procedure_title": "Đăng ký tạm trú",
            "route": "/cu-tru/dang-ky-tam-tru",
        }
    }


@asynccontextmanager
async def _client(
    *outcomes: ExtractionOutcome,
) -> AsyncIterator[AsyncClient]:
    repository = ProcedureRepository.discover()

    def session_factory() -> ConversationSession:
        return ConversationSession(StubExtractor(*outcomes), repository)

    app = create_app(session_factory=session_factory, repository=repository)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


async def _create_session(
    client: AsyncClient,
    *,
    with_supported_context: bool = True,
) -> str:
    response = await client.post(
        "/v1/chat/sessions",
        json=_supported_context() if with_supported_context else {},
    )
    assert response.status_code == 201
    return response.headers["X-VNeGuide-Session"]


async def _patch_field(
    client: AsyncClient,
    session_id: str,
    field_id: str,
    value: object,
    expected_revision: int,
) -> Response:
    return await client.patch(
        f"/v1/chat/sessions/{session_id}/draft/fields/{field_id}",
        json={"value": value, "expected_revision": expected_revision},
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_create_session_returns_seeded_initial_draft_snapshot() -> None:
    async with _client() as client:
        response = await client.post("/v1/chat/sessions", json=_supported_context())

    assert response.status_code == 201
    assert response.json()["turn"] is None
    assert response.json()["draft"] == {
        "values": {},
        "revision": 0,
        "confirmed_fields": [],
        "dirty_fields": [],
        "pack_version": "2.1.0",
    }


@pytest.mark.anyio
async def test_supported_session_context_seeds_core_and_manual_edit_contract() -> None:
    async with _client() as client:
        session_id = await _create_session(client)

        response = await _patch_field(
            client,
            session_id,
            "temporary_address",
            TEMPORARY_ADDRESS,
            expected_revision=0,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["procedure"]["code"] == TEMPORARY_RESIDENCE_CODE
    assert body["draft"] == {
        "values": {"temporary_address": TEMPORARY_ADDRESS},
        "revision": 1,
        "confirmed_fields": ["temporary_address"],
        "dirty_fields": ["temporary_address"],
        "pack_version": "2.1.0",
    }


@pytest.mark.anyio
async def test_each_valid_manual_edit_increments_revision() -> None:
    async with _client() as client:
        session_id = await _create_session(client)

        first = await _patch_field(
            client,
            session_id,
            "temporary_address",
            TEMPORARY_ADDRESS,
            expected_revision=0,
        )
        second = await _patch_field(
            client,
            session_id,
            "submission_channel",
            "online",
            expected_revision=1,
        )

    assert first.status_code == 200
    assert first.json()["draft"]["revision"] == 1
    assert second.status_code == 200
    assert second.json()["draft"]["revision"] == 2
    assert second.json()["draft"]["values"] == {
        "temporary_address": TEMPORARY_ADDRESS,
        "submission_channel": "online",
    }
    assert second.json()["draft"]["confirmed_fields"] == [
        "submission_channel",
        "temporary_address",
    ]
    assert second.json()["draft"]["dirty_fields"] == [
        "submission_channel",
        "temporary_address",
    ]


@pytest.mark.anyio
async def test_stale_manual_edit_returns_409_without_mutating_state() -> None:
    async with _client() as client:
        session_id = await _create_session(client)
        accepted = await _patch_field(
            client,
            session_id,
            "temporary_address",
            TEMPORARY_ADDRESS,
            expected_revision=0,
        )

        stale = await _patch_field(
            client,
            session_id,
            "temporary_address",
            "Giá trị từ response cũ",
            expected_revision=0,
        )
        recovered = await client.get(f"/v1/chat/sessions/{session_id}")

    assert accepted.status_code == 200
    assert stale.status_code == 409
    assert recovered.status_code == 200
    assert recovered.json()["turn"] == accepted.json()
    assert recovered.json()["draft"] == accepted.json()["draft"]
    assert recovered.json()["turn"]["draft"]["values"] == {"temporary_address": TEMPORARY_ADDRESS}
    assert recovered.json()["turn"]["draft"]["revision"] == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("field_id", "value"),
    [
        ("field_does_not_exist", "anything"),
        ("applicant_is_minor", "yes"),
        ("registration_mode", "unsupported-mode"),
        ("temporary_address", "   "),
    ],
    ids=["unknown-field", "wrong-type", "invalid-enum", "blank-string"],
)
async def test_invalid_manual_edit_returns_422_without_mutating_state(
    field_id: str,
    value: object,
) -> None:
    async with _client() as client:
        session_id = await _create_session(client)
        before = await client.get(f"/v1/chat/sessions/{session_id}")

        invalid = await _patch_field(
            client,
            session_id,
            field_id,
            value,
            expected_revision=0,
        )
        after = await client.get(f"/v1/chat/sessions/{session_id}")
        still_current = await _patch_field(
            client,
            session_id,
            "temporary_address",
            TEMPORARY_ADDRESS,
            expected_revision=0,
        )

    assert invalid.status_code == 422
    assert after.status_code == 200
    assert after.json()["turn"] == before.json()["turn"]
    assert still_current.status_code == 200
    assert still_current.json()["draft"]["revision"] == 1


@pytest.mark.anyio
@pytest.mark.parametrize("value_token", ["NaN", "Infinity", "-Infinity"])
async def test_non_finite_manual_number_returns_422_without_mutation(
    value_token: str,
) -> None:
    async with _client() as client:
        created = await client.post(
            "/v1/chat/sessions",
            json={"context": {"procedure_code": "1.013314"}},
        )
        assert created.status_code == 201
        session_id = created.headers["X-VNeGuide-Session"]

        invalid = await client.patch(
            f"/v1/chat/sessions/{session_id}/draft/fields/floor_area_m2",
            content=f'{{"value":{value_token},"expected_revision":0}}',
            headers={"Content-Type": "application/json"},
        )
        recovered = await client.get(f"/v1/chat/sessions/{session_id}")

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_field_value"
    assert recovered.status_code == 200
    assert recovered.json()["draft"]["revision"] == 0
    assert recovered.json()["draft"]["values"] == {}


@pytest.mark.anyio
async def test_manual_edit_without_active_procedure_returns_409_without_mutation() -> None:
    async with _client() as client:
        session_id = await _create_session(client, with_supported_context=False)
        before = await client.get(f"/v1/chat/sessions/{session_id}")

        response = await _patch_field(
            client,
            session_id,
            "temporary_address",
            TEMPORARY_ADDRESS,
            expected_revision=0,
        )
        after = await client.get(f"/v1/chat/sessions/{session_id}")

    assert response.status_code == 409
    assert after.status_code == 200
    assert after.json()["turn"] == before.json()["turn"]


@pytest.mark.anyio
async def test_get_session_recovers_the_latest_manual_edit_result() -> None:
    async with _client() as client:
        session_id = await _create_session(client)
        edited = await _patch_field(
            client,
            session_id,
            "submission_channel",
            "online",
            expected_revision=0,
        )

        recovered = await client.get(f"/v1/chat/sessions/{session_id}")

    assert edited.status_code == 200
    assert recovered.status_code == 200
    assert recovered.json()["turn"] == edited.json()
    assert recovered.json()["turn"]["draft"]["values"] == {"submission_channel": "online"}


@pytest.mark.anyio
async def test_manual_edit_invalidates_pending_suggestion_for_the_same_field() -> None:
    suggested_address = "Số 1 đường Gợi Ý, Hà Nội"
    outcome = ExtractionOutcome(
        status="success",
        classification="supported",
        procedure_code=TEMPORARY_RESIDENCE_CODE,
        fields={"temporary_address": suggested_address},
        evidence={"temporary_address": suggested_address},
        clarification_question=None,
        attempts=1,
    )
    async with _client(outcome) as client:
        session_id = await _create_session(client)
        suggested = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": f"Địa chỉ tạm trú là {suggested_address}"},
        )
        pending = [
            item
            for item in suggested.json()["suggestions"]
            if item["field_id"] == "temporary_address" and item["status"] == "pending"
        ]
        assert len(pending) == 1

        edited = await _patch_field(
            client,
            session_id,
            "temporary_address",
            TEMPORARY_ADDRESS,
            expected_revision=0,
        )

    assert edited.status_code == 200
    assert edited.json()["draft"]["values"]["temporary_address"] == TEMPORARY_ADDRESS
    assert "temporary_address" in edited.json()["draft"]["confirmed_fields"]
    assert "temporary_address" in edited.json()["draft"]["dirty_fields"]
    assert not any(
        item["field_id"] == "temporary_address" and item["status"] == "pending"
        for item in edited.json()["suggestions"]
    )


@pytest.mark.anyio
async def test_delete_then_new_session_starts_with_a_clean_draft() -> None:
    async with _client() as client:
        first_session_id = await _create_session(client)
        first_edit = await _patch_field(
            client,
            first_session_id,
            "temporary_address",
            TEMPORARY_ADDRESS,
            expected_revision=0,
        )
        deleted = await client.delete(f"/v1/chat/sessions/{first_session_id}")
        old_session = await client.get(f"/v1/chat/sessions/{first_session_id}")

        second_session_id = await _create_session(client)
        second_edit = await _patch_field(
            client,
            second_session_id,
            "submission_channel",
            "direct",
            expected_revision=0,
        )

    assert first_edit.status_code == 200
    assert deleted.status_code == 204
    assert old_session.status_code == 404
    assert second_session_id != first_session_id
    assert second_edit.status_code == 200
    assert second_edit.json()["draft"]["revision"] == 1
    assert second_edit.json()["draft"]["values"] == {"submission_channel": "direct"}
    assert "temporary_address" not in second_edit.json()["draft"]["values"]
