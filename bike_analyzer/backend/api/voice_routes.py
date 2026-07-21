"""Voice assistant API routes.

Provides endpoints for:
- STT (Speech-to-Text): transcribe audio blobs to text
- TTS (Text-to-Speech): synthesize text to audio
- Voice commands listing
- Full assistant pipeline

Primary STT backend: Groq Whisper API (fast, no local GPU needed).
Primary TTS backend: edge-tts (free, natural voices, no API key).
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from ..settings import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)
_s = get_settings()

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class STTResponse(BaseModel):
    text: str
    language: str | None = None
    backend: str


class TTSRequest(BaseModel):
    text: str
    voice: str = "it-IT-IsabellaNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"


class TTSResponse(BaseModel):
    audio_url: str
    format: str = "mp3"
    voice: str


class AssistantRequest(BaseModel):
    text: str | None = None
    session_id: str | None = None


class AssistantResponse(BaseModel):
    text: str
    audio_url: str | None = None
    session_id: str
    intent: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _groq_stt(audio_bytes: bytes, filename: str = "audio.webm") -> str | None:
    """Transcribe audio using Groq Whisper API."""
    api_key = _s.groq_api_key
    if not api_key:
        return None

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {
        "file": (filename, audio_bytes, "audio/webm"),
        "model": (None, "whisper-large-v3-turbo"),
    }
    data = {
        "language": "it",
        "response_format": "json",
        "temperature": 0.0,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            text = result.get("text", "").strip()
            return text or None
    except Exception as exc:
        logger.warning("Groq STT failed: %s", exc)
        return None


async def _edge_tts(text: str, voice: str = "it-IT-IsabellaNeural") -> bytes | None:
    """Synthesize speech using edge-tts."""
    try:
        import edge_tts

        communicate = edge_tts.Communicate(text, voice)
        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])
        audio_buffer.seek(0)
        return audio_buffer.read()
    except Exception as exc:
        logger.warning("edge-tts failed: %s", exc)
        return None


def _groq_chat_response(messages: list[dict[str, str]]) -> str | None:
    """Get chat completion from Groq for the assistant brain."""
    api_key = _s.groq_api_key
    if not api_key:
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _s.groq_model or "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 256,
        "temperature": 0.3,
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return (content or "").strip()
    except Exception as exc:
        logger.warning("Groq chat failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/voice/stt")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Query("it", description="Language hint (it/en)"),
) -> STTResponse:
    """Transcribe an uploaded audio file to text.

    Primary backend: Groq Whisper API.
    The audio file is consumed in-memory and not stored.
    """
    allowed_types = {"audio/webm", "audio/wav", "audio/mp3", "audio/ogg", "audio/mpeg", "audio/x-wav"}
    if file.content_type not in allowed_types:
        # Accept anyway but log
        logger.info("STT received content_type=%s", file.content_type)

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Try Groq Whisper first
    text = await _groq_stt(audio_bytes, filename=file.filename or "audio.webm")
    backend = "groq-whisper"

    if text is None:
        # Fallback: try browser-side STT hint
        raise HTTPException(
            status_code=503,
            detail="STT service unavailable. Use browser speech recognition.",
        )

    return STTResponse(text=text, language=language, backend=backend)


@router.post("/voice/tts")
async def synthesize_speech(request: TTSRequest) -> TTSResponse:
    """Synthesize text to speech audio.

    Primary backend: edge-tts (Microsoft Edge neural voices).
    Returns a temporary URL to download the MP3.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    audio_bytes = await _edge_tts(text, voice=request.voice)
    if audio_bytes is None:
        raise HTTPException(status_code=503, detail="TTS service unavailable")

    # Save to temp file and return URL
    tmp_dir = Path(tempfile.gettempdir()) / "bikemaster_voice"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = tmp_dir / f"tts_{abs(hash(text)) % 10_000_000}.mp3"
    tmp_file.write_bytes(audio_bytes)

    return TTSResponse(
        audio_url=f"/api/v1/voice/tts/audio/{tmp_file.name}",
        format="mp3",
        voice=request.voice,
    )


@router.get("/voice/tts/audio/{filename}")
async def get_tts_audio(filename: str):
    """Serve a generated TTS audio file."""
    tmp_file = Path(tempfile.gettempdir()) / "bikemaster_voice" / filename
    if not tmp_file.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(
        path=str(tmp_file),
        media_type="audio/mpeg",
        filename=filename,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/voice/commands")
async def list_voice_commands() -> dict[str, Any]:
    """List all supported voice commands."""
    return {
        "commands": [
            {"id": "nav.open", "label": "Apri vista", "examples": ["apri calendario", "vai alle uscite"]},
            {"id": "athlete.update_weight", "label": "Aggiorna peso", "examples": ["peso 70 kg"]},
            {"id": "athlete.update_height", "label": "Aggiorna altezza", "examples": ["altezza 175 cm"]},
            {"id": "athlete.update_ftp", "label": "Aggiorna FTP", "examples": ["ftp 250 watt"]},
            {"id": "athlete.update_max_hr", "label": "Aggiorna FC max", "examples": ["fc max 180"]},
            {"id": "calendar.add_event", "label": "Aggiungi evento", "examples": ["calendario aggiungi ride martedi"]},
            {"id": "rides.add", "label": "Aggiungi uscita", "examples": ["aggiungi uscita 80 km"]},
            {"id": "nutrition.log_meal", "label": "Registra pasto", "examples": ["colazione cappuccino cornetto"]},
            {"id": "tracking.start", "label": "Avvia tracciamento", "examples": ["inizia tracciamento"]},
            {"id": "tracking.stop", "label": "Ferma tracciamento", "examples": ["ferma tracciamento"]},
            {"id": "settings.toggle_theme", "label": "Cambia tema", "examples": ["cambia tema"]},
            {"id": "settings.toggle_sidebar", "label": "Mostra/nascondi sidebar", "examples": ["mostra sidebar"]},
        ],
        "languages": ["it-IT", "en-US"],
    }


@router.post("/voice/assistant")
async def voice_assistant(request: AssistantRequest) -> AssistantResponse:
    """Full voice assistant pipeline: text in -> brain response + TTS audio out.

    This is the main endpoint for the conversational voice assistant.
    It receives text (from STT or text input), processes it through the
    assistant brain, and returns a text response with optional TTS audio.
    """
    text = (request.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    session_id = request.session_id or "default"

    # Build conversation context
    messages = [
        {
            "role": "system",
            "content": (
                "Sei l'assistente vocale di BikeMaster, un'app di ciclismo e salute. "
                "Rispondi in italiano in modo conciso e naturale, come Google Assistant o Alexa. "
                "Sei utile, amichevole e diretto. "
                "Non fare discorsi lunghi. Risposte massimo 2 frasi. "
                "Puoi aiutare con: uscite di ciclismo, alimentazione, calendario allenamenti, "
                "dati atleta (peso, FTP, FC max), meteo, mappe, tracciamento GPS, impostazioni. "
                "Se non capisci, chiedi di ripetere."
            ),
        },
    ]

    # Add user message
    messages.append({"role": "user", "content": text})

    # Get response from Groq
    response_text = _groq_chat_response(messages)
    if response_text is None:
        response_text = "Mi dispiace, non ho capito. Puoi ripetere?"

    # Generate TTS audio
    audio_url = None
    audio_bytes = await _edge_tts(response_text, voice="it-IT-IsabellaNeural")
    if audio_bytes:
        tmp_dir = Path(tempfile.gettempdir()) / "bikemaster_voice"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = tmp_dir / f"assistant_{abs(hash(response_text)) % 10_000_000}.mp3"
        tmp_file.write_bytes(audio_bytes)
        audio_url = f"/api/v1/voice/tts/audio/{tmp_file.name}"

    # Detect simple intent for frontend actions
    intent = _detect_intent(text)

    return AssistantResponse(
        text=response_text,
        audio_url=audio_url,
        session_id=session_id,
        intent=intent,
    )


def _detect_intent(text: str) -> str | None:
    """Simple keyword-based intent detection for frontend actions."""
    lower = text.lower()
    if any(w in lower for w in ["apri", "vai a", "mostra", "calendario", "uscite", "dashboard", "mappe"]):
        return "navigation"
    if any(w in lower for w in ["peso", "altezza", "ftp", "fc max", "frequenza cardiaca"]):
        return "athlete_update"
    if any(w in lower for w in ["aggiungi uscita", "nuova uscita", "registra uscita"]):
        return "add_ride"
    if any(w in lower for w in ["colazione", "pranzo", "cena", "pasto", "alimentazione"]):
        return "log_meal"
    if any(w in lower for w in ["inizia tracciamento", "avvia", "parti"]):
        return "start_tracking"
    if any(w in lower for w in ["ferma", "stop", "termina"]):
        return "stop_tracking"
    if any(w in lower for w in ["tema", "sidebar", "impostazioni"]):
        return "settings"
    return "general"
