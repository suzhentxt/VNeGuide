"""Bounded localhost job worker for multimodal Qwen OCR requests."""

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
from typing import Literal, Protocol

from fastapi import FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from vneguide.ai.config import load_llm_config
from vneguide.data import ProcedureRepository

from .config import OcrConfig, load_ocr_config
from .errors import OcrInputError
from .models import OcrDocument, OcrResult
from .preprocess import MAX_FILE_BYTES, SafeDocumentPreprocessor
from .provider import QwenVisionBackend
from .service import OcrService

JobStatus = Literal["queued", "running", "succeeded", "manual_input", "failed"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictModel):
    status: Literal["ready", "degraded"]
    model_id: str
    provider: Literal["litellm"] = "litellm"


class CandidateResponse(StrictModel):
    field_id: str
    suggested_value: str | int | float | bool | None
    confidence: float
    evidence: str
    source: Literal["USER_UPLOAD"]


class JobCreatedResponse(StrictModel):
    job_id: str
    status: Literal["queued"] = "queued"


class JobResponse(StrictModel):
    job_id: str
    status: JobStatus
    document_type: str | None = None
    candidates: list[CandidateResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    duration_ms: int = 0


@dataclass(slots=True)
class OcrJob:
    job_id: str
    created_at: float
    updated_at: float
    status: JobStatus = "queued"
    result: OcrResult | None = None
    error_code: str | None = None


class OcrExtractor(Protocol):
    def extract_ct01(self, document: OcrDocument) -> OcrResult: ...


class OcrJobManager:
    def __init__(
        self,
        service: OcrExtractor,
        *,
        max_queued: int = 2,
        timeout_seconds: int = 300,
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

    def submit(self, document: OcrDocument) -> str:
        with self._lock:
            self._mark_timeouts_locked()
            self._cleanup_locked()
            active = sum(job.status in {"queued", "running"} for job in self._jobs.values())
            if active >= self._max_queued:
                raise RuntimeError("ocr_queue_full")
            job_id = secrets.token_urlsafe(24)
            now = self._clock()
            self._jobs[job_id] = OcrJob(job_id=job_id, created_at=now, updated_at=now)
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
                job_id=job.job_id,
                created_at=job.created_at,
                updated_at=job.updated_at,
                status=job.status,
                result=job.result,
                error_code=job.error_code,
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
        try:
            result = self._service.extract_ct01(document)
        except OcrInputError as exc:
            with self._lock:
                job = self._jobs.get(job_id)
                if job is not None and job.status == "running":
                    job.status = "failed"
                    job.error_code = exc.code
                    job.updated_at = self._clock()
            return
        except Exception:
            with self._lock:
                job = self._jobs.get(job_id)
                if job is not None and job.status == "running":
                    job.status = "failed"
                    job.error_code = "ocr_worker_failed"
                    job.updated_at = self._clock()
            return
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
            job.status = "manual_input"
            job.error_code = "ocr_timeout"
            job.result = OcrResult(
                status="manual_input",
                document_type="uncertain",
                warnings=("manual_input_available",),
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
        title="VNeGuide Local OCR Worker",
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
        ready = config.enabled and config.worker_token is not None
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
        x_form_id: str | None = Header(default=None),
    ) -> JobCreatedResponse:
        authorize(authorization)
        if x_procedure_code != "1.004194" or x_form_id != "CT01":
            raise HTTPException(status_code=422, detail="unsupported_ocr_scope")
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_FILE_BYTES:
                    raise HTTPException(status_code=413, detail="file_too_large")
            except ValueError:
                raise HTTPException(status_code=422, detail="invalid_content_length") from None
        body = await request.body()
        if len(body) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="file_too_large")
        try:
            document = OcrDocument(
                content=body,
                declared_mime=request.headers.get("content-type", ""),
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid_ocr_document") from None
        try:
            job_id = job_manager.submit(document)
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
            job = job_manager.get(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="ocr_job_not_found") from None
        return _serialize_job(job)

    return app


def _serialize_job(job: OcrJob) -> JobResponse:
    result = job.result
    if result is None:
        return JobResponse(job_id=job.job_id, status=job.status, error_code=job.error_code)
    candidates: list[CandidateResponse] = []
    for candidate in result.candidates:
        value = candidate.suggested_value
        if not isinstance(value, (str, int, float, bool)) and value is not None:
            continue
        candidates.append(
            CandidateResponse(
                field_id=candidate.field_id,
                suggested_value=value,
                confidence=candidate.confidence,
                evidence=candidate.evidence,
                source=candidate.source,
            )
        )
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        document_type=result.document_type,
        candidates=candidates,
        warnings=list(result.warnings),
        error_code=result.error_code,
        duration_ms=result.duration_ms,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the VNeGuide Qwen OCR worker")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--env-file", default=".env")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("OCR worker may only bind to localhost")
    config = load_ocr_config()
    if not config.enabled or config.worker_token is None:
        raise SystemExit("Enable OCR and configure its worker token before starting it")
    llm_config = load_llm_config(env_file=args.env_file)
    if llm_config.model != config.model_id:
        raise SystemExit("OCR model must match VNEGUIDE_MODEL from the selected env file")
    backend = QwenVisionBackend(llm_config, timeout_seconds=config.job_timeout_seconds)
    service = OcrService(
        SafeDocumentPreprocessor(),
        backend,
        ProcedureRepository.discover(),
    )
    app = create_worker_app(service, config)
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning", access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["OcrJob", "OcrJobManager", "create_worker_app", "main"]
