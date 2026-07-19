from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
from httpx import ASGITransport, AsyncClient

pytest.importorskip("multipart", reason="voice adapter tests require python-multipart")


def _load_module() -> ModuleType:
    path = Path(__file__).parents[2] / "deployment" / "voice-adapter" / "app.py"
    spec = importlib.util.spec_from_file_location("vneguide_voice_adapter", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


voice_adapter = _load_module()


def _settings(**overrides: object):
    values = {
        "inbound_api_key": "incoming-secret",
        "upstream_url": "http://vneguide-stt:9208/v1/audio/transcriptions",
        "max_bytes": 128,
        "max_duration_seconds": 60,
        "timeout_seconds": 5,
        "max_concurrency": 1,
        "max_response_bytes": 65_536,
    }
    values.update(overrides)
    return voice_adapter.Settings(**values)


def test_secret_file_has_priority_over_environment(monkeypatch, tmp_path: Path) -> None:
    secret_file = tmp_path / "adapter-key"
    secret_file.write_text("file-secret", encoding="utf-8")
    monkeypatch.setenv("TEST_SECRET_FILE", str(secret_file))
    monkeypatch.setenv("TEST_SECRET_ENV", "environment-secret")

    assert voice_adapter._read_secret("TEST_SECRET_FILE", "TEST_SECRET_ENV") == "file-secret"


def test_configured_secret_file_fails_closed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TEST_SECRET_FILE", str(tmp_path / "missing"))
    monkeypatch.setenv("TEST_SECRET_ENV", "environment-secret")

    with pytest.raises(RuntimeError, match="does not exist"):
        voice_adapter._read_secret("TEST_SECRET_FILE", "TEST_SECRET_ENV")


@pytest.mark.parametrize("invalid", ["secret\n", "secret\r", "secret\0value", "x" * 4_097])
def test_secret_rejects_unsafe_values(invalid: str) -> None:
    with pytest.raises(RuntimeError):
        voice_adapter._validate_secret(invalid, "test")


@pytest.mark.parametrize(
    "url",
    [
        "http://asr:9208/v1/audio/transcriptions?token=secret",
        "http://asr:9208/v1/audio/transcriptions#fragment",
    ],
)
def test_upstream_url_rejects_query_and_fragment(url: str) -> None:
    with pytest.raises(RuntimeError):
        voice_adapter._validated_upstream_url(url)


@pytest.mark.anyio
async def test_ffprobe_rejects_actual_duration_above_limit(monkeypatch, tmp_path: Path) -> None:
    commands: list[list[str]] = []

    async def fake_run(command: list[str], timeout_seconds: int) -> bytes:
        del timeout_seconds
        commands.append(command)
        return b"60.001\n"

    monkeypatch.setattr(voice_adapter, "_run_process", fake_run)
    with pytest.raises(OverflowError, match="too long"):
        await voice_adapter._probe_and_convert(
            tmp_path / "input.webm",
            tmp_path / "normalized.wav",
            max_duration_seconds=60,
            timeout_seconds=5,
        )

    assert commands[0][0] == "ffprobe"
    assert len(commands) == 1


@pytest.mark.anyio
async def test_ffmpeg_normalizes_to_16khz_mono(monkeypatch, tmp_path: Path) -> None:
    commands: list[list[str]] = []

    async def fake_run(command: list[str], timeout_seconds: int) -> bytes:
        del timeout_seconds
        commands.append(command)
        if command[0] == "ffprobe":
            return b"12.5\n"
        Path(command[-1]).write_bytes(b"RIFF" + b"\0" * 64)
        return b""

    monkeypatch.setattr(voice_adapter, "_run_process", fake_run)
    duration = await voice_adapter._probe_and_convert(
        tmp_path / "input.webm",
        tmp_path / "normalized.wav",
        max_duration_seconds=60,
        timeout_seconds=5,
    )

    assert duration == 12.5
    ffmpeg = commands[1]
    assert ffmpeg[0] == "ffmpeg"
    assert ffmpeg[ffmpeg.index("-ac") + 1] == "1"
    assert ffmpeg[ffmpeg.index("-ar") + 1] == "16000"


@pytest.mark.anyio
async def test_health_does_not_expose_secrets() -> None:
    application = voice_adapter.create_app(
        _settings(upstream_api_key="upstream-secret", upstream_url="http://private-asr:9208/v1")
    )
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert "incoming-secret" not in serialized
    assert "upstream-secret" not in serialized
    assert "private-asr" not in serialized


@pytest.mark.anyio
async def test_transcription_requires_valid_bearer_token() -> None:
    application = voice_adapter.create_app(_settings())
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/audio/transcriptions",
            files={"file": ("sample.wav", b"RIFF", "audio/wav")},
        )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.anyio
async def test_rejects_unlisted_mime_before_media_processing() -> None:
    application = voice_adapter.create_app(_settings())
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/audio/transcriptions",
            headers={"Authorization": "Bearer incoming-secret"},
            files={"file": ("payload.bin", b"not audio", "application/octet-stream")},
        )

    assert response.status_code == 415


@pytest.mark.anyio
async def test_rejects_audio_larger_than_configured_limit() -> None:
    application = voice_adapter.create_app(_settings(max_bytes=4))
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/audio/transcriptions",
            headers={"Authorization": "Bearer incoming-secret"},
            files={"file": ("sample.wav", b"12345", "audio/wav")},
        )

    assert response.status_code == 413


@pytest.mark.anyio
async def test_happy_path_normalizes_and_pins_upstream_model(tmp_path: Path) -> None:
    application = voice_adapter.create_app(_settings())
    observed: dict[str, object] = {}

    async def fake_convert(input_path: Path, output_path: Path, **kwargs: object) -> float:
        observed["input"] = input_path.read_bytes()
        observed["convert"] = kwargs
        output_path.write_bytes(b"RIFF" + b"\0" * 64)
        return 1.0

    async def fake_forward(wav_path: Path, **kwargs: object) -> str:
        observed["wav"] = wav_path.read_bytes()
        observed["forward"] = kwargs
        return voice_adapter._normalize_transcript("  Xin\n chào   Việt Nam  ")

    application.state.probe_and_convert = fake_convert
    application.state.forward_to_upstream = fake_forward
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/audio/transcriptions",
            headers={"Authorization": "Bearer incoming-secret"},
            data={"model": "attacker/model", "language": "vi"},
            files={"file": ("sample.wav", b"RIFF-sample", "audio/wav")},
        )

    assert response.status_code == 200
    assert response.json() == {"text": "Xin chào Việt Nam"}
    assert observed["input"] == b"RIFF-sample"
    assert observed["wav"] == b"RIFF" + b"\0" * 64
    assert observed["forward"]["settings"].upstream_model == "Qwen/Qwen3-ASR-0.6B-hf"


@pytest.mark.anyio
async def test_concurrency_overload_returns_429() -> None:
    application = voice_adapter.create_app(_settings(max_concurrency=1))
    entered = asyncio.Event()
    release = asyncio.Event()

    async def fake_convert(input_path: Path, output_path: Path, **kwargs: object) -> float:
        del input_path, kwargs
        output_path.write_bytes(b"RIFF" + b"\0" * 64)
        return 1.0

    async def blocking_forward(wav_path: Path, **kwargs: object) -> str:
        del wav_path, kwargs
        entered.set()
        await release.wait()
        return "xong"

    application.state.probe_and_convert = fake_convert
    application.state.forward_to_upstream = blocking_forward
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as first_client:
        first = asyncio.create_task(
            first_client.post(
                "/v1/audio/transcriptions",
                headers={"Authorization": "Bearer incoming-secret"},
                files={"file": ("one.wav", b"RIFF-one", "audio/wav")},
            )
        )
        await entered.wait()
        async with AsyncClient(transport=transport, base_url="http://test") as second_client:
            second = await second_client.post(
                "/v1/audio/transcriptions",
                headers={"Authorization": "Bearer incoming-secret"},
                files={"file": ("two.wav", b"RIFF-two", "audio/wav")},
            )
        release.set()
        first_response = await first

    assert second.status_code == 429
    assert first_response.status_code == 200
