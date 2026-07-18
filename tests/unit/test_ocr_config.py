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


def test_ocr_reuses_the_generic_api_key_when_no_dedicated_key_exists() -> None:
    config = load_ocr_config({"VNEGUIDE_API_KEY": "shared-synthetic-key"})
    assert config.api_key == "shared-synthetic-key"


def test_ocr_loads_worker_configuration_from_env_file(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VNEGUIDE_OCR_ENABLED=true\n"
        "VNEGUIDE_API_KEY=shared-synthetic-key\n"
        "VNEGUIDE_OCR_WORKER_TOKEN=synthetic-worker-token\n",
        encoding="utf-8",
    )
    config = load_ocr_config({}, env_file=env_file)
    assert config.enabled is True
    assert config.api_key == "shared-synthetic-key"
    assert config.worker_token == "synthetic-worker-token"


def test_ocr_rejects_non_positive_limits() -> None:
    with pytest.raises(ValueError, match="positive"):
        load_ocr_config({"VNEGUIDE_OCR_JOB_TIMEOUT_SECONDS": "0"})
