from __future__ import annotations

import pytest

from vneguide.ocr.config import load_ocr_config


def test_ocr_is_disabled_and_secretless_by_default() -> None:
    config = load_ocr_config({})
    assert config.enabled is False
    assert config.model_id == "gpt-5.5"
    assert config.api_key is None
    assert config.worker_token is None


def test_ocr_uses_dedicated_openai_configuration() -> None:
    config = load_ocr_config(
        {
            "VNEGUIDE_OCR_ENABLED": "1",
            "VNEGUIDE_OCR_MODEL": "vision-test-model",
            "VNEGUIDE_OCR_OPENAI_API_KEY": "synthetic-api-key",
            "VNEGUIDE_OCR_WORKER_TOKEN": "synthetic-worker-token",
            "VNEGUIDE_MODEL": "chat-model-must-not-leak",
        }
    )
    assert config.enabled is True
    assert config.model_id == "vision-test-model"
    assert config.api_key == "synthetic-api-key"
    assert config.worker_token == "synthetic-worker-token"


def test_ocr_rejects_non_positive_limits() -> None:
    with pytest.raises(ValueError, match="positive"):
        load_ocr_config({"VNEGUIDE_OCR_JOB_TIMEOUT_SECONDS": "0"})
