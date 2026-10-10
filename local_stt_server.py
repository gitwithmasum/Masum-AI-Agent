from __future__ import annotations

import asyncio
import os
import re
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
WAKE_MODEL_NAME = os.getenv("LOCAL_WAKE_MODEL", "tiny").strip() or "tiny"
DEVICE = os.getenv("LOCAL_STT_DEVICE", "cpu").strip() or "cpu"
COMPUTE_TYPE = os.getenv("LOCAL_STT_COMPUTE_TYPE", "int8").strip() or "int8"
MODEL_DIR = Path(os.getenv("LOCAL_STT_MODEL_DIR", "data/stt_models"))
MAX_AUDIO_BYTES = int(
    os.getenv("LOCAL_STT_MAX_AUDIO_BYTES", str(20 * 1024 * 1024))
)
BEAM_SIZE = int(os.getenv("LOCAL_STT_BEAM_SIZE", "5"))
WAKE_BEAM_SIZE = int(os.getenv("LOCAL_WAKE_BEAM_SIZE", "1"))
WAKE_PHRASES = [
    item.strip()
    for item in os.getenv(
        "LOCAL_WAKE_PHRASES",
        "hey cirilla,cirilla,hey sirilla,sirilla,cirila,"
        "সিরিলা,হেই সিরিলা",
    ).split(",")
    if item.strip()
]

MODEL_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Masum Local STT",
    version="4.2.0",
    docs_url=None,
    redoc_url=None,
)

_model: WhisperModel | None = None
_wake_model: WhisperModel | None = None
_model_lock = threading.Lock()
_transcribe_lock = asyncio.Lock()


def build_model(model_name: str) -> WhisperModel:
    return WhisperModel(
        model_name,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
        download_root=str(MODEL_DIR),
    )


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
            _model = build_model(MODEL_NAME)
    return _model


def get_wake_model() -> WhisperModel:
    global _wake_model
    if _wake_model is not None:
        return _wake_model

    with _model_lock:
        if _wake_model is None:
            print(
                f"Loading Cirilla wake model '{WAKE_MODEL_NAME}' "
                f"on {DEVICE}/{COMPUTE_TYPE}..."
            )
            _wake_model = build_model(WAKE_MODEL_NAME)
    return _wake_model


def suffix_for_content_type(content_type: str) -> str:
    value = (content_type or "").lower()
    if "ogg" in value:
        return ".ogg"
    if "wav" in value:
        return ".wav"
    if "mp4" in value or "m4a" in value:
        return ".m4a"
    return ".webm"


def collect_text(segments) -> str:
    values = []
    for segment in segments:
        text = (segment.text or "").strip()
        if text:
            values.append(text)
    return " ".join(values).strip()


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

    return {
        "text": collect_text(segments),
        "language": getattr(info, "language", None),
        "language_probability": getattr(
            info,
            "language_probability",
            None,
        ),
        "model": MODEL_NAME,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
    }


def normalize_phrase(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(
        r"[^\w\s]+",
        " ",
        value,
        flags=re.UNICODE,
    )
    return re.sub(r"\s+", " ", value).strip()


def find_wake_phrase(text: str) -> str | None:
    normalized = normalize_phrase(text)
    for phrase in WAKE_PHRASES:
        if normalize_phrase(phrase) in normalized:
            return phrase
    return None


def wake_transcribe_file(
    file_path: str,
    language: str,
) -> dict:
    model = get_wake_model()
    language_arg = None if language == "auto" else language

    segments, info = model.transcribe(
        file_path,
        language=language_arg,
        beam_size=max(1, min(WAKE_BEAM_SIZE, 3)),
        vad_filter=True,
        condition_on_previous_text=False,
    )

    text = collect_text(segments)
    matched = find_wake_phrase(text)

    return {
        "text": text,
        "wake_detected": matched is not None,
        "matched_phrase": matched,
        "language": getattr(info, "language", None),
        "language_probability": getattr(
            info,
            "language_probability",
            None,
        ),
        "model": WAKE_MODEL_NAME,
    }


async def save_request_audio(
    request: Request,
) -> str:
    audio = await request.body()
    if not audio:
        raise HTTPException(
            status_code=400,
            detail="Audio body is empty.",
        )
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Audio exceeds the configured size limit.",
        )

    suffix = suffix_for_content_type(
        request.headers.get("content-type", "")
    )
    handle = tempfile.NamedTemporaryFile(
        suffix=suffix,
        delete=False,
    )
    try:
        handle.write(audio)
        return handle.name
    finally:
        handle.close()


@app.get("/status")
async def status():
    return {
        "online": True,
        "model": MODEL_NAME,
        "loaded": _model is not None,
        "wake_model": WAKE_MODEL_NAME,
        "wake_loaded": _wake_model is not None,
        "wake_name": "Cirilla",
        "wake_phrases": WAKE_PHRASES,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "model_dir": str(MODEL_DIR),
    }


@app.post("/transcribe")
async def transcribe(
    request: Request,
    language: str = "bn",
):
    language = language.strip().lower()
    if language not in {"bn", "en", "auto"}:
        language = "auto"

    path = None
    try:
        path = await save_request_audio(request)
        async with _transcribe_lock:
            return await asyncio.to_thread(
                transcribe_file,
                path,
                language,
            )
    except HTTPException:
        raise
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


@app.post("/wake-detect")
async def wake_detect(
    request: Request,
    language: str = "auto",
):
    language = language.strip().lower()
    if language not in {"bn", "en", "auto"}:
        language = "auto"

    path = None
    try:
        path = await save_request_audio(request)
        async with _transcribe_lock:
            return await asyncio.to_thread(
                wake_transcribe_file,
                path,
                language,
            )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Wake detection failed: {error}",
        ) from error
    finally:
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    print("=" * 64)
    print("🎙️ MASUM LOCAL STT v4.2 — CIRILLA WAKE MODE")
    print(f"Service : http://{HOST}:{PORT}")
    print(f"STT     : {MODEL_NAME}")
    print(f"Wake    : {WAKE_MODEL_NAME} | Cirilla")
    print(f"Device  : {DEVICE} / {COMPUTE_TYPE}")
    print(f"Cache   : {MODEL_DIR}")
    print("Wake Mode is opt-in from the dashboard.")
    print("=" * 64)

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="warning",
    )
