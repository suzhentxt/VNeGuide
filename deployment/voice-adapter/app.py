"""Authenticated, OpenAI-compatible speech-to-text adapter.

The public edge (for example Cloudflare Tunnel) calls this service.  The
actual Qwen ASR service stays on a private Docker network.  This module never
logs request bodies, transcripts, bearer tokens, or upstream credentials.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import math
import os
import tempfile
import unicodedata
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

DEFAULT_ALLOWED_MIME_TYPES = frozenset(
    {
        "application/ogg",
        "audio/flac",
        "audio/mp4",
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "audio/webm",
        "audio/x-flac",
        "audio/x-m4a",
        "audio/x-wav",
    }
)
MIME_SUFFIXES = {
    "application/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
    "audio/x-flac": ".flac",
    "audio/x-m4a": ".m4a",
    "audio/x-wav": ".wav",
}
READ_CHUNK_BYTES = 64 * 1024
MULTIPART_OVERHEAD_ALLOWANCE = 128 * 1024
MAX_SECRET_CHARACTERS = 4_096


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    try:
        value = default if raw is None else int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


def _validate_secret(value: str, source_name: str) -> str:
    if not value:
        raise RuntimeError(f"Secret configured by {source_name} is empty")
    if len(value) > MAX_SECRET_CHARACTERS:
        raise RuntimeError(f"Secret configured by {source_name} is too large")
    if "\0" in value or "\r" in value or "\n" in value:
        raise RuntimeError(f"Secret configured by {source_name} contains invalid characters")
    if value != value.strip():
        raise RuntimeError(f"Secret configured by {source_name} contains surrounding whitespace")
    return value


def _read_secret(file_name: str, env_name: str) -> str:
    """Read a secret from a file first, then fall back to an environment value."""

    path_value = os.getenv(file_name, "").strip()
    if path_value:
        path = Path(path_value)
        if not path.is_file():
            raise RuntimeError(f"Secret file configured by {file_name} does not exist")
        try:
            value = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise RuntimeError(f"Unable to read secret configured by {file_name}") from exc
        return _validate_secret(value, file_name)
    value = os.getenv(env_name, "")
    return _validate_secret(value, env_name) if value else ""


def _validated_upstream_url(raw: str) -> str:
    value = raw.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("VNEGUIDE_VOICE_ADAPTER_UPSTREAM_URL must be an HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError("Upstream URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise RuntimeError("Upstream URL must not contain a query or fragment")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    inbound_api_key: str
    upstream_url: str
    upstream_api_key: str = ""
    upstream_model: str = "Qwen/Qwen3-ASR-0.6B-hf"
    max_bytes: int = 4_000_000
    max_duration_seconds: int = 60
    timeout_seconds: int = 60
    max_concurrency: int = 1
    max_response_bytes: int = 65_536
    allowed_mime_types: frozenset[str] = DEFAULT_ALLOWED_MIME_TYPES

    @classmethod
    def from_env(cls) -> Settings:
        allowed_raw = os.getenv("VNEGUIDE_VOICE_ADAPTER_ALLOWED_MIME_TYPES", "")
        allowed = (
            frozenset(item.strip().lower() for item in allowed_raw.split(",") if item.strip())
            if allowed_raw
            else DEFAULT_ALLOWED_MIME_TYPES
        )
        if not allowed:
            raise RuntimeError("At least one audio MIME type must be allowed")
        return cls(
            inbound_api_key=_read_secret(
                "VNEGUIDE_VOICE_ADAPTER_API_KEY_FILE",
                "VNEGUIDE_VOICE_ADAPTER_API_KEY",
            ),
            upstream_url=_validated_upstream_url(
                os.getenv(
                    "VNEGUIDE_VOICE_ADAPTER_UPSTREAM_URL",
                    "http://vneguide-stt:9208/v1/audio/transcriptions",
                )
            ),
            upstream_api_key=_read_secret(
                "VNEGUIDE_VOICE_ADAPTER_UPSTREAM_API_KEY_FILE",
                "VNEGUIDE_VOICE_ADAPTER_UPSTREAM_API_KEY",
            ),
            upstream_model=os.getenv(
                "VNEGUIDE_VOICE_ADAPTER_UPSTREAM_MODEL", "Qwen/Qwen3-ASR-0.6B-hf"
            ).strip(),
            max_bytes=_env_int(
                "VNEGUIDE_VOICE_ADAPTER_MAX_BYTES", 4_000_000, minimum=1, maximum=20_000_000
            ),
            max_duration_seconds=_env_int(
                "VNEGUIDE_VOICE_ADAPTER_MAX_DURATION_SECONDS", 60, minimum=1, maximum=600
            ),
            timeout_seconds=_env_int(
                "VNEGUIDE_VOICE_ADAPTER_TIMEOUT_SECONDS", 60, minimum=1, maximum=300
            ),
            max_concurrency=_env_int(
                "VNEGUIDE_VOICE_ADAPTER_MAX_CONCURRENCY", 1, minimum=1, maximum=32
            ),
            max_response_bytes=_env_int(
                "VNEGUIDE_VOICE_ADAPTER_MAX_RESPONSE_BYTES",
                65_536,
                minimum=1_024,
                maximum=1_048_576,
            ),
            allowed_mime_types=allowed,
        )


class ConcurrencyGate:
    """Small non-queuing concurrency gate; overload is rejected immediately."""

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._active = 0
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        async with self._lock:
            if self._active >= self._limit:
                raise HTTPException(status_code=429, detail="Speech service is busy")
            self._active += 1
        try:
            yield
        finally:
            async with self._lock:
                self._active -= 1


async def _run_process(command: list[str], timeout_seconds: int) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except BaseException:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                process.kill()
            await process.communicate()
        raise
    if process.returncode != 0:
        raise ValueError("Media validation failed")
    return stdout


async def _probe_and_convert(
    input_path: Path,
    output_path: Path,
    *,
    max_duration_seconds: int,
    timeout_seconds: int,
) -> float:
    probe_output = await _run_process(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(input_path),
        ],
        min(timeout_seconds, 15),
    )
    try:
        duration = float(probe_output.decode("ascii", errors="strict").strip())
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Audio duration is unavailable") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Audio duration is invalid")
    if duration > max_duration_seconds:
        raise OverflowError("Audio is too long")

    await _run_process(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(input_path),
            "-map_metadata",
            "-1",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ],
        timeout_seconds,
    )
    if not output_path.is_file() or output_path.stat().st_size <= 44:
        raise ValueError("Converted audio is empty")
    return duration


def _normalize_transcript(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Upstream transcript is not text")
    return " ".join(unicodedata.normalize("NFC", value).split())


async def _read_limited_response(response: httpx.Response, limit: int) -> bytes:
    body = bytearray()
    async for chunk in response.aiter_bytes():
        if len(body) + len(chunk) > limit:
            raise OverflowError("Upstream response is too large")
        body.extend(chunk)
    return bytes(body)


async def _forward_to_upstream(
    wav_path: Path,
    *,
    settings: Settings,
    language: str | None,
    prompt: str | None,
) -> str:
    fields: dict[str, str] = {"model": settings.upstream_model}
    if language:
        fields["language"] = language
    if prompt:
        fields["prompt"] = prompt
    headers = {}
    if settings.upstream_api_key:
        headers["Authorization"] = f"Bearer {settings.upstream_api_key}"

    timeout = httpx.Timeout(settings.timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        with wav_path.open("rb") as audio:
            files = {"file": ("audio.wav", audio, "audio/wav")}
            async with client.stream(
                "POST",
                settings.upstream_url,
                headers=headers,
                data=fields,
                files=files,
            ) as response:
                if response.status_code < 200 or response.status_code >= 300:
                    await response.aclose()
                    raise RuntimeError("Upstream transcription failed")
                body = await _read_limited_response(response, settings.max_response_bytes)
    try:
        payload = json.loads(body)
        return _normalize_transcript(payload["text"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Upstream transcription response is invalid") from exc


async def _store_upload(upload: UploadFile, destination: Path, max_bytes: int) -> int:
    total = 0
    with destination.open("wb") as output:
        while chunk := await upload.read(READ_CHUNK_BYTES):
            total += len(chunk)
            if total > max_bytes:
                raise OverflowError("Audio file is too large")
            output.write(chunk)
    if total == 0:
        raise ValueError("Audio file is empty")
    return total


def _verify_bearer(authorization: str | None, expected: str) -> None:
    if not expected:
        raise HTTPException(status_code=503, detail="Speech adapter is not configured")
    scheme, separator, supplied = (authorization or "").partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not supplied:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings or Settings.from_env()
    gate = ConcurrencyGate(configured.max_concurrency)
    application = FastAPI(
        title="VNeGuide Voice Adapter",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.state.settings = configured
    application.state.probe_and_convert = _probe_and_convert
    application.state.forward_to_upstream = _forward_to_upstream

    @application.middleware("http")
    async def protect_transcription(request: Request, call_next: Any) -> Any:
        if request.url.path == "/v1/audio/transcriptions":
            try:
                _verify_bearer(request.headers.get("authorization"), configured.inbound_api_key)
            except HTTPException as exc:
                return JSONResponse(
                    {"detail": exc.detail},
                    status_code=exc.status_code,
                    headers=exc.headers,
                )
            raw_length = request.headers.get("content-length")
            if raw_length:
                try:
                    content_length = int(raw_length)
                except ValueError:
                    return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
                if content_length < 0:
                    return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
                if content_length > configured.max_bytes + MULTIPART_OVERHEAD_ALLOWANCE:
                    return JSONResponse({"detail": "Audio file is too large"}, status_code=413)
        return await call_next(request)

    @application.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok" if configured.inbound_api_key else "degraded",
            "ready": bool(configured.inbound_api_key),
            "limits": {
                "max_bytes": configured.max_bytes,
                "max_duration_seconds": configured.max_duration_seconds,
                "max_concurrency": configured.max_concurrency,
            },
        }

    @application.post("/v1/audio/transcriptions")
    async def transcribe(
        file: Annotated[UploadFile, File(...)],
        model: Annotated[str | None, Form()] = None,
        language: Annotated[str | None, Form()] = None,
        prompt: Annotated[str | None, Form()] = None,
    ) -> JSONResponse:
        del model  # Clients may send it; the adapter always pins the configured upstream model.

        mime_type = (file.content_type or "").partition(";")[0].strip().lower()
        if mime_type not in configured.allowed_mime_types:
            raise HTTPException(status_code=415, detail="Unsupported audio media type")
        if language is not None and len(language) > 32:
            raise HTTPException(status_code=400, detail="Language value is too long")
        if prompt is not None and len(prompt) > 1_000:
            raise HTTPException(status_code=400, detail="Prompt is too long")

        try:
            async with gate.slot():
                async with asyncio.timeout(configured.timeout_seconds):
                    suffix = MIME_SUFFIXES.get(mime_type, ".audio")
                    with tempfile.TemporaryDirectory(prefix="vneguide-voice-") as temporary:
                        input_path = Path(temporary) / f"input{suffix}"
                        output_path = Path(temporary) / "normalized.wav"
                        await _store_upload(file, input_path, configured.max_bytes)
                        await application.state.probe_and_convert(
                            input_path,
                            output_path,
                            max_duration_seconds=configured.max_duration_seconds,
                            timeout_seconds=configured.timeout_seconds,
                        )
                        text = await application.state.forward_to_upstream(
                            output_path,
                            settings=configured,
                            language=language,
                            prompt=prompt,
                        )
                        return JSONResponse({"text": text})
        except OverflowError as exc:
            message = str(exc)
            if "long" in message:
                raise HTTPException(status_code=422, detail="Audio duration exceeds limit") from exc
            if "response" in message:
                raise HTTPException(status_code=502, detail="Invalid upstream response") from exc
            raise HTTPException(status_code=413, detail="Audio file is too large") from exc
        except TimeoutError as exc:
            raise HTTPException(status_code=504, detail="Speech processing timed out") from exc
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="Speech processing timed out") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Speech provider is unavailable") from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=502, detail="Speech provider rejected the request"
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="Invalid audio or provider response"
            ) from exc
        finally:
            await file.close()

    return application


app = create_app()
