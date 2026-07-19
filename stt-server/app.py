"""OpenAI-compatible STT micro-service wrapping Qwen3-ASR (transformers, CPU).

Exposes POST /v1/audio/transcriptions so the VNeGuide demoweb (stt-config.ts)
can point VNEGUIDE_STT_BASE_URL here and the Mic button lights up.

Model + loading logic mirror vn-en-translator/app/asr.py::Qwen3ASRTorchBackend:
repo Qwen/Qwen3-ASR-0.6B-hf, fp32, CPU, AutoProcessor.apply_transcription_request.
"""

from __future__ import annotations

import io
import os
from typing import Optional

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

SAMPLE_RATE = 16_000
MODEL_REPO = os.getenv("STT_MODEL_REPO", "Qwen/Qwen3-ASR-0.6B-hf")

app = FastAPI(title="VNeGuide STT", version="1.0.0")

_state: dict = {}


@app.on_event("startup")
def _load() -> None:
    from transformers import AutoProcessor, Qwen3ASRForConditionalGeneration

    torch.set_num_threads(os.cpu_count() or 4)
    proc = AutoProcessor.from_pretrained(MODEL_REPO)
    model = Qwen3ASRForConditionalGeneration.from_pretrained(
        MODEL_REPO, dtype=torch.float32, device_map="cpu"
    )
    model.eval()
    # warmup: stabilize first real call (ML graph / mel-frame padding)
    with torch.no_grad():
        warm = proc.apply_transcription_request(
            audio=np.zeros(SAMPLE_RATE, dtype=np.float32),
            language=None,
            return_tensors="pt",
        ).to("cpu")
        model.generate(**warm, max_new_tokens=8)
    _state["proc"] = proc
    _state["model"] = model
    _state["torch"] = torch


@app.get("/health")
def health() -> dict:
    ready = "model" in _state
    return {"status": "ok" if ready else "loading", "model": MODEL_REPO, "ready": ready}


@app.get("/v1/models")
def models() -> dict:
    return {"data": [{"id": MODEL_REPO, "object": "model"}]}


def _decode_audio(raw: bytes) -> np.ndarray:
    """Decode arbitrary audio bytes to 16kHz mono float32."""
    data, sr = sf.read(io.BytesIO(raw), always_2d=False, dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != SAMPLE_RATE:
        # resample via simple linear interp (avoids scipy/librosa dep)
        n = int(round(len(data) * SAMPLE_RATE / sr))
        idx = np.linspace(0, len(data) - 1, n)
        data = np.interp(idx, np.arange(len(data)), data).astype(np.float32)
    peak = float(np.max(np.abs(data))) if data.size else 0.0
    if peak > 0:
        data = data / peak
    return np.ascontiguousarray(data, dtype=np.float32)


@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
):
    if "model" not in _state:
        return JSONResponse({"error": "model not ready"}, status_code=503)
    raw = await file.read()
    if not raw:
        return JSONResponse({"error": "empty audio"}, status_code=400)
    try:
        samples = _decode_audio(raw)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": f"decode failed: {exc}"}, status_code=400)
    if samples.size < 160:
        return JSONResponse({"text": ""})

    proc = _state["proc"]
    th = _state["torch"]
    # Qwen3-ASR expects language=None for built-in LID; honor "vi"/"en" only.
    lang_arg = language if language in ("vi", "en") else None
    inputs = proc.apply_transcription_request(
        audio=samples, language=lang_arg, return_tensors="pt"
    ).to("cpu")
    with th.no_grad():
        out = _state["model"].generate(**inputs, max_new_tokens=256)
    gen = out[:, inputs["input_ids"].shape[1]:]
    parsed = proc.decode(gen[0], return_format="parsed")
    text = (parsed.get("transcription") or "").strip() if isinstance(parsed, dict) else str(parsed)
    return {"text": text}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "9208")))
