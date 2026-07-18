from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from vneguide.ai import (
    ExtractionCatalog,
    ExtractionOutcome,
    ExtractionTurnContext,
    MockLLMProvider,
    ProviderTimeout,
    StructuredExtractor,
)
from vneguide.api import create_app
from vneguide.core import ConversationSession
from vneguide.data import ProcedureRepository

Scalar = str | int | float | bool

SUPPORTED_PROCEDURES = {
    "2.000635",
    "1.013314",
    "1.004194",
}

COMPLETE_CASES: dict[str, dict[str, Scalar]] = {
    "2.000635": {
        "requester_type": "self",
        "requester_full_name": "Người Yêu Cầu Kiểm Thử",
        "requester_personal_id": "000000000000",
        "subject_full_name": "Người Được Trích Lục Kiểm Thử",
        "subject_date_of_birth": "2000-01-01",
        "copies_requested": 1,
        "submission_channel": "online",
    },
    "1.013314": {
        "requester_full_name": "Người Yêu Cầu Kiểm Thử",
        "requester_date_of_birth": "1990-01-01",
        "requester_personal_id": "000000000000",
        "requester_residence": "Địa chỉ tổng hợp, Hà Nội",
        "legal_dwelling_address": "Chỗ ở tổng hợp, Hà Nội",
        "floor_area_m2": 60,
        "current_permanent_residents": 2,
        "remaining_floor_area_m2": 30,
        "new_residents_count": 2,
        "allocated_area_m2": 30,
        "hanoi_zone": "inner_city",
        "declared_stable_use": True,
        "declared_no_dispute": True,
        "declared_not_prohibited_location": True,
    },
    "1.004194": {
        "registration_mode": "individual_or_household",
        "applicant_full_name": "Người Đăng Ký Kiểm Thử",
        "applicant_date_of_birth": "1990-01-01",
        "applicant_personal_id": "000000000000",
        "applicant_is_minor": False,
        "temporary_address": "Chỗ ở tạm trú tổng hợp, Hà Nội",
        "temporary_start_date": "2026-08-01",
        "temporary_end_date": "2027-08-01",
        "legal_dwelling_data_retrievable": True,
        "dwelling_basis": "rented",
        "owner_or_householder_consent": True,
        "submission_channel": "online",
        "fee_exemption_claimed": False,
    },
}


class StubExtractor:
    def __init__(self, *outcomes: ExtractionOutcome) -> None:
        self._outcomes = deque(outcomes)

    def extract(
        self,
        _message: str,
        *,
        context: ExtractionTurnContext | None = None,
    ) -> ExtractionOutcome:
        del context
        return self._outcomes.popleft()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def outcome(
    *,
    classification: str = "supported",
    procedure_code: str | None = None,
    fields: Mapping[str, Scalar] | None = None,
    status: str = "success",
    error_code: str | None = None,
) -> ExtractionOutcome:
    values = {} if fields is None else dict(fields)
    return ExtractionOutcome(
        status=status,
        classification=classification if status == "success" else None,
        procedure_code=procedure_code if status == "success" else None,
        fields=values,
        evidence={field_id: "Dữ liệu tổng hợp do QA cung cấp" for field_id in values},
        clarification_question=None,
        attempts=1,
        error_code=error_code,
    )


def app_for(*outcomes: ExtractionOutcome) -> FastAPI:
    repository = ProcedureRepository.discover()

    def session_factory() -> ConversationSession:
        return ConversationSession(StubExtractor(*outcomes), repository)

    return create_app(session_factory=session_factory, repository=repository)


async def create_session(client: AsyncClient, procedure_code: str | None = None) -> str:
    context = (
        None
        if procedure_code is None
        else {
            "procedure_code": procedure_code,
            "procedure_title": "Kịch bản kiểm thử phát hành",
            "route": f"/thu-tuc/{procedure_code}",
        }
    )
    response = await client.post("/v1/chat/sessions", json={"context": context})
    assert response.status_code == 201
    assert response.json()["context_supported"] is True
    return response.headers["X-VNeGuide-Session"]


async def accept_all(
    client: AsyncClient,
    session_id: str,
    turn: dict[str, Any],
) -> dict[str, Any]:
    current = turn
    while True:
        pending = [item for item in current["suggestions"] if item["status"] == "pending"]
        if not pending:
            return current
        suggestion = pending[0]
        response = await client.post(
            f"/v1/chat/sessions/{session_id}/suggestions/{suggestion['id']}",
            json={"action": "accept", "expected_revision": suggestion["revision"]},
        )
        assert response.status_code == 200
        current = response.json()


@pytest.mark.anyio
@pytest.mark.parametrize("procedure_code", sorted(SUPPORTED_PROCEDURES))
async def test_release_routes_exactly_three_reviewed_procedures(procedure_code: str) -> None:
    repository = ProcedureRepository.discover()
    assert {pack.procedure_code.value for pack in repository.list_procedures()} == (
        SUPPORTED_PROCEDURES
    )
    field_id, value = next(iter(COMPLETE_CASES[procedure_code].items()))
    app = app_for(outcome(procedure_code=procedure_code, fields={field_id: value}))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        session_id = await create_session(client, procedure_code)
        response = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": "Tôi cần hỗ trợ thủ tục này."},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["procedure"]["code"] == procedure_code
    assert body["next_action"] == "confirm_suggestion"
    assert body["draft"]["confirmed_fields"] == []
    assert body["sources"]


@pytest.mark.anyio
async def test_release_rejects_out_of_scope_without_populating_draft() -> None:
    app = app_for(outcome(classification="unsupported"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        session_id = await create_session(client)
        response = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": "Tôi cần bản sao trích lục kết hôn."},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["next_action"] == "out_of_scope"
    assert body["procedure"] is None
    assert body["draft"]["confirmed_fields"] == []
    assert body["suggestions"] == []
    assert body["sources"] == []


@pytest.mark.anyio
@pytest.mark.parametrize("run_number", range(1, 6))
async def test_temporary_residence_hero_flow_passes_five_of_five_runs(
    run_number: int,
) -> None:
    procedure_code = "1.004194"
    app = app_for(outcome(procedure_code=procedure_code, fields=COMPLETE_CASES[procedure_code]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1/5 — a supported session is created with the temporary-residence context.
        session_id = await create_session(client, procedure_code)

        # 2/5 — extraction creates suggestions but never writes unconfirmed values to the draft.
        first = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": f"Tôi đăng ký tạm trú online tại nhà thuê, lượt {run_number}."},
        )
        first_turn = first.json()
        assert first_turn["procedure"]["code"] == procedure_code
        assert first_turn["suggestions"]
        assert first_turn["draft"]["confirmed_fields"] == []

        # 3/5 — a manual correction is explicit and marks the field dirty.
        name_suggestion = next(
            item for item in first_turn["suggestions"] if item["field_id"] == "applicant_full_name"
        )
        edited = await client.post(
            f"/v1/chat/sessions/{session_id}/suggestions/{name_suggestion['id']}",
            json={
                "action": "edit",
                "value": "Người Đăng Ký Đã Sửa",
                "expected_revision": name_suggestion["revision"],
            },
        )
        edited_turn = edited.json()
        assert edited.status_code == 200
        assert edited_turn["draft"]["dirty_fields"] == ["applicant_full_name"]

        # 4/5 — every remaining suggestion is accepted against its rebased revision.
        final_turn = await accept_all(client, session_id, edited_turn)
        assert len(final_turn["draft"]["confirmed_fields"]) == len(COMPLETE_CASES[procedure_code])

        # 5/5 — deterministic validation reaches ready, then reset invalidates the old session.
        assert final_turn["next_action"] == "complete"
        assert final_turn["validation"]["status"] == "ready_to_submit"
        reset = await client.delete(f"/v1/chat/sessions/{session_id}")
        stale_session = await client.get(f"/v1/chat/sessions/{session_id}")
        replacement_id = await create_session(client, procedure_code)

    assert reset.status_code == 204
    assert stale_session.status_code == 404
    assert replacement_id != session_id


@pytest.mark.anyio
async def test_stale_revision_is_rejected_after_another_suggestion_changes_draft() -> None:
    app = app_for(
        outcome(
            procedure_code="2.000635",
            fields={"copies_requested": 1, "submission_channel": "online"},
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        session_id = await create_session(client, "2.000635")
        turn = (
            await client.post(
                f"/v1/chat/sessions/{session_id}/messages",
                json={"message": "Tôi muốn xin một bản trực tuyến."},
            )
        ).json()
        first, stale = turn["suggestions"]
        accepted = await client.post(
            f"/v1/chat/sessions/{session_id}/suggestions/{first['id']}",
            json={"action": "accept", "expected_revision": first["revision"]},
        )
        response = await client.post(
            f"/v1/chat/sessions/{session_id}/suggestions/{stale['id']}",
            json={"action": "accept", "expected_revision": stale["revision"]},
        )

    assert accepted.status_code == 200
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stale_suggestion"


async def assert_repeated_failure_offers_manual_fallback(app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        session_id = await create_session(client)
        first = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": "Hệ thống chưa đọc được dữ liệu tổng hợp."},
        )
        second = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={"message": "Tôi thử lại với dữ liệu tổng hợp."},
        )
        session = await client.get(f"/v1/chat/sessions/{session_id}")

    assert first.status_code == 200
    assert first.json()["next_action"] == "retry"
    assert second.status_code == 200
    assert second.json()["next_action"] == "manual_input"
    assert session.status_code == 200
    assert session.json()["turn"]["draft"]["confirmed_fields"] == []


@pytest.mark.anyio
async def test_typed_provider_timeout_preserves_session_and_offers_manual_fallback() -> None:
    repository = ProcedureRepository.discover()
    catalog = ExtractionCatalog.from_data_package(repository.paths.root)

    def session_factory() -> ConversationSession:
        provider = MockLLMProvider([ProviderTimeout("synthetic timeout") for _ in range(4)])
        return ConversationSession(StructuredExtractor(provider, catalog), repository)

    app = create_app(session_factory=session_factory, repository=repository)
    await assert_repeated_failure_offers_manual_fallback(app)


@pytest.mark.anyio
async def test_generic_ocr_upstream_failure_uses_safe_manual_fallback() -> None:
    fallback = outcome(status="fallback", error_code="ocr_unreadable")
    await assert_repeated_failure_offers_manual_fallback(app_for(fallback, fallback))
