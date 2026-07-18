from __future__ import annotations

import threading

from fastapi.testclient import TestClient

from vneguide.ocr import OcrCandidate, OcrDocument, OcrResult
from vneguide.ocr.config import OcrConfig
from vneguide.ocr.worker import OcrJobManager, create_worker_app


class ImmediateService:
    def extract_ct01(self, _document: OcrDocument) -> OcrResult:
        return OcrResult(
            status="succeeded",
            document_type="CT01",
            candidates=(OcrCandidate("temporary_address", "Địa chỉ thử nghiệm", 0.91, "visible"),),
        )


class BlockingService:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def extract_ct01(self, _document: OcrDocument) -> OcrResult:
        self.started.set()
        self.release.wait(timeout=2)
        return OcrResult(status="manual_input", document_type="uncertain")


def _config() -> OcrConfig:
    return OcrConfig(
        enabled=True,
        model_id="Qwen/Qwen3.5-9B",
        worker_token="synthetic-test-token",
    )


def test_worker_requires_token_and_ct01_scope() -> None:
    manager = OcrJobManager(ImmediateService())
    app = create_worker_app(ImmediateService(), _config(), manager=manager)
    with TestClient(app) as client:
        unauthorized = client.post(
            "/v1/ocr/jobs",
            headers={"content-type": "image/png"},
            content=b"fake",
        )
        wrong_scope = client.post(
            "/v1/ocr/jobs",
            headers={
                "authorization": "Bearer synthetic-test-token",
                "content-type": "image/png",
                "x-procedure-code": "2.000635",
                "x-form-id": "CT01",
            },
            content=b"fake",
        )

    assert unauthorized.status_code == 401
    assert wrong_scope.status_code == 422


def test_worker_rejects_empty_upload() -> None:
    manager = OcrJobManager(ImmediateService())
    app = create_worker_app(ImmediateService(), _config(), manager=manager)
    with TestClient(app) as client:
        response = client.post(
            "/v1/ocr/jobs",
            headers={
                "authorization": "Bearer synthetic-test-token",
                "content-type": "image/png",
                "x-procedure-code": "1.004194",
                "x-form-id": "CT01",
            },
            content=b"",
        )
    assert response.status_code == 422


def test_worker_returns_candidate_contract() -> None:
    manager = OcrJobManager(ImmediateService())
    app = create_worker_app(ImmediateService(), _config(), manager=manager)
    headers = {
        "authorization": "Bearer synthetic-test-token",
        "content-type": "image/png",
        "x-procedure-code": "1.004194",
        "x-form-id": "CT01",
    }
    with TestClient(app) as client:
        created = client.post("/v1/ocr/jobs", headers=headers, content=b"fake")
        assert created.status_code == 202
        job_id = created.json()["job_id"]
        response = client.get(
            f"/v1/ocr/jobs/{job_id}",
            headers={"authorization": "Bearer synthetic-test-token"},
        )
        for _ in range(100):
            if response.json()["status"] not in {"queued", "running"}:
                break
            response = client.get(
                f"/v1/ocr/jobs/{job_id}",
                headers={"authorization": "Bearer synthetic-test-token"},
            )

    assert response.status_code == 200
    assert response.json()["candidates"] == [
        {
            "field_id": "temporary_address",
            "suggested_value": "Địa chỉ thử nghiệm",
            "confidence": 0.91,
            "evidence": "visible",
            "source": "USER_UPLOAD",
        }
    ]


def test_running_job_times_out_to_manual_input() -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    service = BlockingService()
    manager = OcrJobManager(service, timeout_seconds=1, clock=clock)
    try:
        job_id = manager.submit(OcrDocument(b"fake", "image/png"))
        assert service.started.wait(timeout=1)
        now[0] = 2.0

        job = manager.get(job_id)

        assert job.status == "manual_input"
        assert job.error_code == "ocr_timeout"
        assert job.result is not None
        assert job.result.candidates == ()
    finally:
        service.release.set()
        manager.close()


def test_queued_job_also_times_out_when_previous_inference_is_stuck() -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    service = BlockingService()
    manager = OcrJobManager(service, max_queued=2, timeout_seconds=1, clock=clock)
    try:
        first_id = manager.submit(OcrDocument(b"first", "image/png"))
        assert service.started.wait(timeout=1)
        second_id = manager.submit(OcrDocument(b"second", "image/png"))
        now[0] = 2.0

        assert manager.get(first_id).status == "manual_input"
        assert manager.get(second_id).status == "manual_input"
    finally:
        service.release.set()
        manager.close()
