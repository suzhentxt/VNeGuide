from __future__ import annotations

import pytest

from vneguide.ocr.config import load_ocr_config


def test_ocr_is_disabled_and_secretless_by_default() -> None:
    config = load_ocr_config({})

    assert config.enabled is False
    assert config.model_id == "Qwen/Qwen3.5-9B"
    assert config.worker_token is None


def test_explicit_local_worker_configuration_is_bounded() -> None:
    config = load_ocr_config(
        {
            "VNEGUIDE_OCR_ENABLED": "1",
            "VNEGUIDE_MODEL": "Qwen/Qwen3.5-9B",
            "VNEGUIDE_OCR_WORKER_TOKEN": "synthetic-test-token",
            "VNEGUIDE_OCR_MAX_QUEUED_JOBS": "1",
        }
    )

    assert config.enabled is True
    assert config.model_id == "Qwen/Qwen3.5-9B"
    assert config.max_queued_jobs == 1


def test_invalid_limits_fail_closed() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        load_ocr_config({"VNEGUIDE_OCR_JOB_TIMEOUT_SECONDS": "0"})
