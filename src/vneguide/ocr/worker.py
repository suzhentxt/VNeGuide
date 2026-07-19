"""Bounded asynchronous worker for OpenAI-backed document validation."""

from __future__ import annotations

import argparse
import hmac
import secrets
import threading
import time
from collections.abc import AsyncIterator, Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from fastapi import FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from .config import OcrConfig, load_ocr_config
from .errors import OcrBackendError, OcrInputError
from .models import (
    DocumentKind,
    DocumentValidationBackend,
    ModelAssessment,
    OcrDocument,
    OcrResult,
    PreparedPage,
)
from .preprocess import MAX_FILE_BYTES, SafeDocumentPreprocessor
from .provider import OpenAIDocumentValidationBackend
from .service import OcrService

JobStatus = Literal["queued", "running", "pass", "needs_review", "fail"]
_DOCUMENT_KINDS = frozenset({"legal_dwelling", "minor_consent"})
_CHECK_MESSAGES = {
    "name_valid": "Tài liệu có họ tên người liên quan hợp lệ.",
    "date_valid": "Tài liệu có ngày tháng hợp lệ.",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictModel):
    status: Literal["ready", "degraded"]
    model_id: str
    provider: Literal["openai"] = "openai"


class CheckResponse(StrictModel):
    code: str
    result: Literal["pass", "uncertain", "fail"]
    message: str


class JobCreatedResponse(StrictModel):
    job_id: str
    status: Literal["queued"] = "queued"


class JobResponse(StrictModel):
    job_id: str
    status: JobStatus
    document_kind: DocumentKind
    checks: list[CheckResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    duration_ms: int = 0


@dataclass(slots=True)
class OcrJob:
    job_id: str
    document_kind: DocumentKind
    created_at: float
    updated_at: float
    status: JobStatus = "queued"
    result: OcrResult | None = None
    error_code: str | None = None


class OcrExtractor(Protocol):
    def validate_document(
        self,
        document_kind: DocumentKind,
        document: OcrDocument,
    ) -> OcrResult: ...


class _UnavailableBackend:
    def assess(
        self,
        _document_kind: DocumentKind,
        _pages: Sequence[PreparedPage],
    ) -> ModelAssessment:
        raise OcrBackendError("ocr_disabled", "OCR chưa được cấu hình.")


class OcrJobManager:
    def __init__(
        self,
        service: OcrExtractor,
        *,
        max_queued: int = 2,
        timeout_seconds: int = 60,
        result_ttl_seconds: int = 600,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._service = service
        self._max_queued = max_queued
        self._timeout_seconds = timeout_seconds
        self._result_ttl_seconds = result_ttl_seconds
        self._clock = clock
        self._jobs: dict[str, OcrJob] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vneguide-ocr")

    def submit(self, document_kind: DocumentKind, document: OcrDocument) -> str:
        with self._lock:
            self._mark_timeouts_locked()
            self._cleanup_locked()
            active = sum(job.status in {"queued", "running"} for job in self._jobs.values())
            if active >= self._max_queued:
                raise RuntimeError("ocr_queue_full")
            job_id = secrets.token_urlsafe(24)
            now = self._clock()
            self._jobs[job_id] = OcrJob(job_id, document_kind, now, now)
            self._executor.submit(self._run, job_id, document)
            return job_id

    def get(self, job_id: str) -> OcrJob:
        with self._lock:
            self._mark_timeouts_locked()
            self._cleanup_locked()
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return OcrJob(
                job.job_id,
                job.document_kind,
                job.created_at,
                job.updated_at,
                job.status,
                job.result,
                job.error_code,
            )

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _run(self, job_id: str, document: OcrDocument) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status != "queued":
                return
            job.status = "running"
            job.updated_at = self._clock()
            document_kind = job.document_kind
        try:
            result = self._service.validate_document(document_kind, document)
        except OcrInputError as exc:
            result = OcrResult(
                status="needs_review",
                document_kind=document_kind,
                warnings=("upload_rejected",),
                error_code=exc.code,
            )
        except Exception:
            result = OcrResult(
                status="needs_review",
                document_kind=document_kind,
                warnings=("official_review_required",),
                error_code="ocr_worker_failed",
            )
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status != "running":
                return
            job.result = result
            job.status = result.status
            job.error_code = result.error_code
            job.updated_at = self._clock()

    def _cleanup_locked(self) -> None:
        now = self._clock()
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status not in {"queued", "running"}
            and now - job.updated_at >= self._result_ttl_seconds
        ]
        for job_id in expired:
            self._jobs.pop(job_id, None)

    def _mark_timeouts_locked(self) -> None:
        now = self._clock()
        for job in self._jobs.values():
            if job.status not in {"queued", "running"}:
                continue
            if now - job.updated_at < self._timeout_seconds:
                continue
            job.status = "needs_review"
            job.error_code = "ocr_timeout"
            job.result = OcrResult(
                status="needs_review",
                document_kind=job.document_kind,
                warnings=("official_review_required",),
                error_code="ocr_timeout",
                duration_ms=self._timeout_seconds * 1_000,
            )
            job.updated_at = now


def create_worker_app(
    service: OcrExtractor,
    config: OcrConfig,
    *,
    manager: OcrJobManager | None = None,
) -> FastAPI:
    job_manager = manager or OcrJobManager(
        service,
        max_queued=config.max_queued_jobs,
        timeout_seconds=config.job_timeout_seconds,
        result_ttl_seconds=config.result_ttl_seconds,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        job_manager.close()

    app = FastAPI(
        title="VNeGuide Document Validation OCR",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    def authorize(authorization: str | None) -> None:
        expected = config.worker_token
        if expected is None:
            raise HTTPException(status_code=503, detail="worker_token_missing")
        prefix = "Bearer "
        if authorization is None or not authorization.startswith(prefix):
            raise HTTPException(status_code=401, detail="unauthorized")
        if not hmac.compare_digest(authorization[len(prefix) :], expected):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        ready = config.enabled and config.worker_token is not None and config.api_key is not None
        return HealthResponse(
            status="ready" if ready else "degraded",
            model_id=config.model_id,
        )

    @app.post(
        "/v1/ocr/jobs",
        response_model=JobCreatedResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def create_job(
        request: Request,
        authorization: str | None = Header(default=None),
        x_procedure_code: str | None = Header(default=None),
        x_document_kind: str | None = Header(default=None),
    ) -> JobCreatedResponse:
        authorize(authorization)
        if x_procedure_code != "1.004194":
            raise HTTPException(status_code=422, detail="unsupported_ocr_scope")
        if x_document_kind not in _DOCUMENT_KINDS:
            raise HTTPException(status_code=422, detail="unsupported_document_kind")
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_FILE_BYTES:
                    raise HTTPException(status_code=413, detail="file_too_large")
            except ValueError:
                raise HTTPException(status_code=422, detail="invalid_content_length") from None
        chunks: list[bytes] = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise HTTPException(status_code=413, detail="file_too_large")
            chunks.append(chunk)
        try:
            document = OcrDocument(
                content=b"".join(chunks),
                declared_mime=request.headers.get("content-type", ""),
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid_ocr_document") from None
        try:
            job_id = job_manager.submit(x_document_kind, document)  # type: ignore[arg-type]
        except RuntimeError:
            raise HTTPException(status_code=429, detail="ocr_queue_full") from None
        return JobCreatedResponse(job_id=job_id)

    @app.get("/v1/ocr/jobs/{job_id}", response_model=JobResponse)
    def get_job(
        job_id: str,
        authorization: str | None = Header(default=None),
    ) -> JobResponse:
        authorize(authorization)
        try:
            return _serialize_job(job_manager.get(job_id))
        except KeyError:
            raise HTTPException(status_code=404, detail="ocr_job_not_found") from None

    return app


def _serialize_job(job: OcrJob) -> JobResponse:
    result = job.result
    if result is None:
        return JobResponse(job_id=job.job_id, status=job.status, document_kind=job.document_kind)
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        document_kind=job.document_kind,
        checks=[
            CheckResponse(
                code=check.code,
                result=check.result,
                message=_CHECK_MESSAGES.get(check.code, "Đã kiểm tra tín hiệu tài liệu."),
            )
            for check in result.checks
        ],
        warnings=list(result.warnings),
        error_code=result.error_code,
        duration_ms=result.duration_ms,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the VNeGuide document OCR worker")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--env-file", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_ocr_config(env_file=args.env_file)
    backend: DocumentValidationBackend
    if config.enabled and config.api_key is not None:
        backend = OpenAIDocumentValidationBackend(
            api_key=config.api_key,
            model=config.model_id,
            timeout_seconds=config.job_timeout_seconds,
        )
    else:
        backend = _UnavailableBackend()
    app = create_worker_app(OcrService(SafeDocumentPreprocessor(), backend), config)
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning", access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["OcrJob", "OcrJobManager", "create_worker_app", "main"]
