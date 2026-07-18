from __future__ import annotations

import time

from fastapi.testclient import TestClient

from vneguide.ocr import DocumentCheck, DocumentKind, OcrDocument, OcrResult
from vneguide.ocr.config import OcrConfig
from vneguide.ocr.worker import OcrJobManager, create_worker_app


class ImmediateService:
    def validate_document(self, document_kind: DocumentKind, _document: OcrDocument) -> OcrResult:
        return OcrResult(
            status="pass",
            document_kind=document_kind,
            checks=(DocumentCheck("document_type_match", "pass", 0.95),),
        )


class SlowService:
    def validate_document(self, document_kind: DocumentKind, _document: OcrDocument) -> OcrResult:
        time.sleep(0.05)
        return OcrResult(status="needs_review", document_kind=document_kind)


def config() -> OcrConfig:
    return OcrConfig(
        enabled=True,
        model_id="gpt-5.5",
        api_key="synthetic-api-key",
        worker_token="synthetic-worker-token",
        max_queued_jobs=2,
        job_timeout_seconds=1,
        result_ttl_seconds=60,
    )


def headers(kind: str = "legal_dwelling") -> dict[str, str]:
    return {
        "Authorization": "Bearer synthetic-worker-token",
        "X-Procedure-Code": "1.004194",
        "X-Document-Kind": kind,
        "Content-Type": "image/png",
    }


def test_worker_requires_auth_scope_and_supported_kind() -> None:
    manager = OcrJobManager(ImmediateService())
    with TestClient(create_worker_app(ImmediateService(), config(), manager=manager)) as client:
        assert client.post("/v1/ocr/jobs", content=b"fake").status_code == 401
        wrong_scope = headers()
        wrong_scope["X-Procedure-Code"] = "2.000635"
        assert client.post("/v1/ocr/jobs", headers=wrong_scope, content=b"fake").status_code == 422
        assert (
            client.post("/v1/ocr/jobs", headers=headers("ct01"), content=b"fake").status_code == 422
        )


def test_worker_creates_and_polls_pii_safe_result() -> None:
    manager = OcrJobManager(ImmediateService())
    with TestClient(create_worker_app(ImmediateService(), config(), manager=manager)) as client:
        created = client.post("/v1/ocr/jobs", headers=headers(), content=b"fake")
        assert created.status_code == 202
        job_id = created.json()["job_id"]
        for _ in range(50):
            response = client.get(
                f"/v1/ocr/jobs/{job_id}",
                headers={"Authorization": "Bearer synthetic-worker-token"},
            )
            if response.json()["status"] not in {"queued", "running"}:
                break
            time.sleep(0.01)
        payload = response.json()
        assert payload["status"] == "pass"
        assert payload["document_kind"] == "legal_dwelling"
        assert payload["checks"] == [
            {
                "code": "document_type_match",
                "result": "pass",
                "message": "Tài liệu có nội dung phù hợp với nhóm đã chọn.",
            }
        ]
        assert "content" not in payload


def test_worker_health_and_streaming_size_cap() -> None:
    manager = OcrJobManager(SlowService())
    with TestClient(create_worker_app(SlowService(), config(), manager=manager)) as client:
        assert client.get("/health").json() == {
            "status": "ready",
            "model_id": "gpt-5.5",
            "provider": "openai",
        }
        too_large = b"x" * (8 * 1024 * 1024 + 1)
        assert client.post("/v1/ocr/jobs", headers=headers(), content=too_large).status_code == 413
