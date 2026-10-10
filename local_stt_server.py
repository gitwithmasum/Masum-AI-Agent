from __future__ import annotations

import asyncio
import os
import tempfile
import threading
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from faster_whisper import WhisperModel

load_dotenv(override=True)

HOST = os.getenv("LOCAL_STT_HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = int(os.getenv("LOCAL_STT_PORT", "8766"))
MODEL_NAME = os.getenv("LOCAL_STT_MODEL", "small").strip() or "small"
DEVICE = os.getenv("LOCAL_STT_DEVICE", "cpu").strip() or "cpu"
COMPUTE_TYPE = os.getenv("LOCAL_STT_COMPUTE_TYPE", "int8").strip() or "int8"
MODEL_DIR = Path(os.getenv("LOCAL_STT_MODEL_DIR", "data/stt_models"))
MAX_AUDIO_BYTES = int(os.getenv("LOCAL_STT_MAX_AUDIO_BYTES", str(20 * 1024 * 1024)))
BEAM_SIZE = int(os.getenv("LOCAL_STT_BEAM_SIZE", "5"))

MODEL_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Masum Local STT",
    version="4.1.0",
    docs_url=None,
    redoc_url=None,
)

_model: WhisperModel | None = None
_model_lock = threading.Lock()
_transcribe_lock = asyncio.Lock()


def get_model() -> WhisperModel:
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is None:
            print(
                f"Loading Faster-Whisper model '{MODEL_NAME}' "
                f"on {DEVICE}/{COMPUTE_TYPE}..."
            )
            _model = WhisperModel(
                MODEL_NAME,
                device=DEVICE,
                compute_type=COMPUTE_TYPE,
                download_root=str(MODEL_DIR),
            )
    return _model


def suffix_for_content_type(content_type: str) -> str:
    value = (content_type or "").lower()
    if "ogg" in value:
        return ".ogg"
    if "wav" in value:
        return ".wav"
    if "mp4" in value or "m4a" in value:
        return ".m4a"
    return ".webm"


def transcribe_file(file_path: str, language: str) -> dict:
    model = get_model()
    language_arg = None if language == "auto" else language

    segments, info = model.transcribe(
        file_path,
        language=language_arg,
        beam_size=max(1, min(BEAM_SIZE, 10)),
        vad_filter=True,
        condition_on_previous_text=False,
    )

    text_parts = []
    for segment in segments:
        value = (segment.text or "").strip()
        if value:
            text_parts.append(value)

    return {
        "text": " ".join(text_parts).strip(),
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "model": MODEL_NAME,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
    }


@app.get("/status")
async def status():
    return {
        "online": True,
        "model": MODEL_NAME,
        "loaded": _model is not None,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "model_dir": str(MODEL_DIR),
    }


@app.post("/transcribe")
async def transcribe(request: Request, language: str = "bn"):
    language = language.strip().lower()
    if language not in {"bn", "en", "auto"}:
        language = "auto"

    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="Audio body is empty.")

    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Audio exceeds the configured size limit.",
        )

    suffix = suffix_for_content_type(
        request.headers.get("content-type", "")
    )

    path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as handle:
            handle.write(audio)
            path = handle.name

        async with _transcribe_lock:
            result = await asyncio.to_thread(
                transcribe_file,
                path,
                language,
            )
        return result
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Local transcription failed: {error}",
        ) from error
    finally:
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    print("=" * 64)
    print("🎙️ MASUM LOCAL STT v4.1 — FASTER-WHISPER")
    print(f"Service : http://{HOST}:{PORT}")
    print(f"Model   : {MODEL_NAME}")
    print(f"Device  : {DEVICE} / {COMPUTE_TYPE}")
    print(f"Cache   : {MODEL_DIR}")
    print("First model load may download model files once.")
    print("=" * 64)

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="warning",
    )
