"""Unit tests for the dev-only LoggingProvider wrapper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vneguide.ai.providers import (
    LoggingProvider,
    MockLLMProvider,
    ProviderError,
    StructuredRequest,
)


def _request(system_prompt: str = "system", user_prompt: str = "user") -> StructuredRequest:
    return StructuredRequest(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_schema={"type": "object"},
        schema_name="test_schema",
        timeout_seconds=5.0,
    )


def test_logs_successful_call_with_response(tmp_path: Path) -> None:
    log_path = tmp_path / "llm.jsonl"
    inner = MockLLMProvider([{"classification": "supported", "procedure_code": "2.000635"}])
    provider = LoggingProvider(inner, log_path=log_path, model="test-model")

    result = provider.generate_structured(_request("sys", "tôi tên Hậu"))

    assert result == {"classification": "supported", "procedure_code": "2.000635"}
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["schema_name"] == "test_schema"
    assert record["model"] == "test-model"
    assert record["system_prompt"] == "sys"
    assert record["user_prompt"] == "tôi tên Hậu"
    assert record["response"] == {"classification": "supported", "procedure_code": "2.000635"}
    assert record["status"] == "success"
    assert "error" not in record
    assert isinstance(record["latency_ms"], int)


def test_logs_error_call_and_reraises(tmp_path: Path) -> None:
    log_path = tmp_path / "llm.jsonl"
    inner = MockLLMProvider([ProviderError("gateway down", retryable=True)])
    provider = LoggingProvider(inner, log_path=log_path, model="test-model")

    with pytest.raises(ProviderError):
        provider.generate_structured(_request())

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["status"] == "error"
    assert record["response"] is None
    assert "ProviderError" in record["error"]
    assert "gateway down" in record["error"]


def test_appends_one_line_per_call(tmp_path: Path) -> None:
    log_path = tmp_path / "llm.jsonl"
    inner = MockLLMProvider([{"v": 1}, {"v": 2}, {"v": 3}])
    provider = LoggingProvider(inner, log_path=log_path, model="m")

    for _ in range(3):
        provider.generate_structured(_request())

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    assert json.loads(lines[0])["response"] == {"v": 1}
    assert json.loads(lines[2])["response"] == {"v": 3}


def test_creates_parent_directory(tmp_path: Path) -> None:
    log_path = tmp_path / "nested" / "deep" / "llm.jsonl"
    inner = MockLLMProvider([{"ok": True}])
    provider = LoggingProvider(inner, log_path=log_path, model="m")

    provider.generate_structured(_request())

    assert log_path.exists()


def test_non_jsonable_response_falls_back_to_repr(tmp_path: Path) -> None:
    log_path = tmp_path / "llm.jsonl"

    class Weird:
        pass

    inner = MockLLMProvider([Weird()])
    provider = LoggingProvider(inner, log_path=log_path, model="m")

    provider.generate_structured(_request())

    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["status"] == "success"
    assert isinstance(record["response"], str)
    assert "Weird" in record["response"]
