"""FastAPI composition root for the browser adapter."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import cast

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from vneguide.core import (
    ProcedureConflictError,
    ProcedureNotSelectedError,
    RevisionConflictError,
    create_session,
)
from vneguide.data import ProcedureRepository
from vneguide.domain import JSONValue, ProcedureCode

from .schemas import (
    ChatTurnResponse,
    CreateSessionRequest,
    ErrorResponse,
    FieldEditRequest,
    HealthResponse,
    MessageRequest,
    SessionResponse,
    SuggestionActionRequest,
)
from .serializers import TurnResultSerializer
from .session_store import (
    ChatSession,
    InMemorySessionStore,
    SessionCapacityError,
    SessionEntry,
    SessionExpiredError,
    SessionNotFoundError,
)


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value


def _error(status_code: int, code: str, message: str, *, retryable: bool = False) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "retryable": retryable}},
    )


@contextmanager
def _acquire(store: InMemorySessionStore, session_id: str) -> Iterator[SessionEntry]:
    try:
        with store.acquire(session_id) as entry:
            yield entry
    except SessionExpiredError as exc:
        raise HTTPException(status_code=410, detail="session_expired") from exc
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session_not_found") from exc


def _session_response(
    entry: SessionEntry,
    store: InMemorySessionStore,
    serializer: TurnResultSerializer,
) -> SessionResponse:
    context = entry.context
    supported = (
        context is None
        or context.procedure_code is None
        or context.procedure_code in {code.value for code in ProcedureCode}
    )
    warning = None
    if not supported:
        warning = (
            "Thủ tục đang xem chưa có procedure pack đã review trong backend; "
            "trợ lý chỉ trả lời trong phạm vi data package hiện hành."
        )
    return SessionResponse(
        expires_in_seconds=store.expires_in(entry),
        context=context,
        context_supported=supported,
        scope_warning=warning,
        draft=serializer.serialize_draft(entry.session.state.draft),
        turn=None if entry.last_result is None else serializer.serialize(entry.last_result),
    )


def create_app(
    *,
    session_factory: Callable[[], ChatSession] = create_session,
    repository: ProcedureRepository | None = None,
    store: InMemorySessionStore | None = None,
) -> FastAPI:
    data_repository = repository or ProcedureRepository.discover()
    session_store = store or InMemorySessionStore(
        session_factory,
        ttl_seconds=_positive_int("VNEGUIDE_SESSION_TTL_SECONDS", 1_800),
        max_active=_positive_int("VNEGUIDE_SESSION_MAX_ACTIVE", 100),
    )
    serializer = TurnResultSerializer(data_repository)
    app = FastAPI(
        title="VNeGuide Chat API",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json",
    )

    @app.exception_handler(HTTPException)
    def handle_http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        if exc.detail == "session_expired":
            return _error(410, "session_expired", "Phiên trò chuyện đã hết hạn.")
        if exc.detail == "session_not_found":
            return _error(404, "session_not_found", "Không tìm thấy phiên trò chuyện.")
        if exc.detail == "session_capacity":
            return _error(
                429,
                "session_capacity",
                "Hệ thống đang có quá nhiều phiên trò chuyện.",
                retryable=True,
            )
        if exc.detail == "stale_suggestion":
            return _error(
                409,
                "stale_suggestion",
                "Đề xuất đã cũ; vui lòng tải trạng thái mới nhất.",
            )
        if exc.detail == "invalid_suggestion":
            return _error(
                409,
                "invalid_suggestion",
                "Đề xuất không còn hợp lệ cho bản nháp hiện tại.",
            )
        if exc.detail == "stale_revision":
            return _error(
                409,
                "stale_revision",
                "Bản nháp đã thay đổi; vui lòng tải trạng thái mới nhất.",
            )
        if exc.detail == "procedure_not_selected":
            return _error(
                409,
                "procedure_not_selected",
                "Hãy chọn thủ tục trước khi cập nhật biểu mẫu.",
            )
        if exc.detail == "procedure_conflict":
            return _error(
                409,
                "procedure_conflict",
                "Thủ tục đang hoạt động không khớp với phiên hiện tại.",
            )
        if exc.detail == "invalid_field_value":
            return _error(
                422,
                "invalid_field_value",
                "Giá trị biểu mẫu không hợp lệ.",
            )
        return _error(exc.status_code, "request_failed", "Không thể xử lý yêu cầu.")

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return _error(422, "invalid_request", "Dữ liệu gửi tới trợ lý không hợp lệ.")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.post(
        "/v1/chat/sessions",
        response_model=SessionResponse,
        responses={429: {"model": ErrorResponse}},
        status_code=status.HTTP_201_CREATED,
    )
    def create_chat_session(payload: CreateSessionRequest, response: Response) -> SessionResponse:
        try:
            session_id, entry = session_store.create(payload.context)
        except SessionCapacityError:
            raise HTTPException(status_code=429, detail="session_capacity") from None
        if payload.context is not None and payload.context.procedure_code is not None:
            try:
                code = ProcedureCode(payload.context.procedure_code)
            except ValueError:
                pass
            else:
                try:
                    entry.session.initialize_procedure(code)
                except ProcedureConflictError:
                    session_store.delete(session_id)
                    raise HTTPException(status_code=409, detail="procedure_conflict") from None
        response.headers["X-VNeGuide-Session"] = session_id
        response.headers["Cache-Control"] = "no-store"
        return _session_response(entry, session_store, serializer)

    @app.get(
        "/v1/chat/sessions/{session_id}",
        response_model=SessionResponse,
        responses={404: {"model": ErrorResponse}, 410: {"model": ErrorResponse}},
    )
    def get_chat_session(session_id: str) -> SessionResponse:
        with _acquire(session_store, session_id) as entry:
            return _session_response(entry, session_store, serializer)

    @app.post(
        "/v1/chat/sessions/{session_id}/messages",
        response_model=ChatTurnResponse,
        responses={404: {"model": ErrorResponse}, 410: {"model": ErrorResponse}},
    )
    def send_message(session_id: str, payload: MessageRequest) -> ChatTurnResponse:
        with _acquire(session_store, session_id) as entry:
            if payload.client_turn_id:
                cached = entry.turn_results.get(payload.client_turn_id)
                if cached is not None:
                    return serializer.serialize(cached)
            result = entry.session.send(payload.message.strip())
            entry.last_result = result
            if payload.client_turn_id:
                entry.turn_results[payload.client_turn_id] = result
                if len(entry.turn_results) > 20:
                    oldest = next(iter(entry.turn_results))
                    entry.turn_results.pop(oldest)
        return serializer.serialize(result)

    @app.post(
        "/v1/chat/sessions/{session_id}/suggestions/{suggestion_id}",
        response_model=ChatTurnResponse,
        responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    )
    def resolve_suggestion(
        session_id: str,
        suggestion_id: str,
        payload: SuggestionActionRequest,
    ) -> ChatTurnResponse:
        with _acquire(session_store, session_id) as entry:
            if entry.session.state.draft.revision != payload.expected_revision:
                raise HTTPException(status_code=409, detail="stale_suggestion")
            try:
                if payload.action == "accept":
                    result = entry.session.accept_suggestion(
                        suggestion_id,
                        expected_revision=payload.expected_revision,
                    )
                elif payload.action == "reject":
                    result = entry.session.reject_suggestion(
                        suggestion_id,
                        expected_revision=payload.expected_revision,
                    )
                else:
                    result = entry.session.edit_suggestion(
                        suggestion_id,
                        cast(JSONValue, payload.value),
                        expected_revision=payload.expected_revision,
                    )
            except RevisionConflictError:
                raise HTTPException(status_code=409, detail="stale_suggestion") from None
            except ValueError:
                raise HTTPException(status_code=409, detail="invalid_suggestion") from None
            entry.last_result = result
        return serializer.serialize(result)

    @app.patch(
        "/v1/chat/sessions/{session_id}/draft/fields/{field_id}",
        response_model=ChatTurnResponse,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
    )
    def edit_draft_field(
        session_id: str,
        field_id: str,
        payload: FieldEditRequest,
    ) -> ChatTurnResponse:
        with _acquire(session_store, session_id) as entry:
            try:
                result = entry.session.edit_field(
                    field_id,
                    cast(JSONValue, payload.value),
                    expected_revision=payload.expected_revision,
                    user_message=(
                        payload.display_label if payload.interaction == "chat_choice" else None
                    ),
                )
            except RevisionConflictError:
                raise HTTPException(status_code=409, detail="stale_revision") from None
            except ProcedureNotSelectedError:
                raise HTTPException(status_code=409, detail="procedure_not_selected") from None
            except ValueError:
                raise HTTPException(status_code=422, detail="invalid_field_value") from None
            entry.last_result = result
        return serializer.serialize(result)

    @app.delete("/v1/chat/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_chat_session(session_id: str) -> Response:
        session_store.delete(session_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app
