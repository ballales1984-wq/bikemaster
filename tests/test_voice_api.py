"""Voice API routes tests."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.api.voice_routes import _detect_intent
from bike_analyzer.backend.db import database as db_mod


@pytest.fixture
def client(db_path):
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    app = create_app()
    return TestClient(app)


def test_voice_commands_list(client):
    resp = client.get("/api/v1/voice/commands")
    assert resp.status_code == 200
    data = resp.json()
    assert "commands" in data
    assert "languages" in data
    assert len(data["commands"]) > 0
    for cmd in data["commands"]:
        assert "id" in cmd
        assert "label" in cmd
        assert "examples" in cmd


def test_voice_stt_no_file(client):
    resp = client.post("/api/v1/voice/stt")
    assert resp.status_code == 422


def test_voice_stt_empty_file(client):
    resp = client.post("/api/v1/voice/stt", files={"file": ("empty.webm", b"", "audio/webm")})
    assert resp.status_code == 400


def test_voice_stt_unallowed_content_type_accepts_but_logs(client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")

    async def fake_groq_stt(audio_bytes, filename):
        return None

    monkeypatch.setattr("bike_analyzer.backend.api.voice_routes._groq_stt", fake_groq_stt)

    resp = client.post(
        "/api/v1/voice/stt",
        files={"file": ("audio.bin", b"fake-audio", "application/octet-stream")},
    )
    assert resp.status_code == 503


def test_voice_tts_empty_text(client):
    resp = client.post("/api/v1/voice/tts", json={"text": ""})
    assert resp.status_code == 400


def test_voice_tts_valid_text_returns_audio_url(client, monkeypatch, tmp_path):
    voice_dir = tmp_path / "bikemaster_voice"
    voice_dir.mkdir(parents=True, exist_ok=True)

    async def fake_edge_tts(text, voice):
        return b"fake-audio-data"

    monkeypatch.setattr("bike_analyzer.backend.api.voice_routes._edge_tts", fake_edge_tts)
    monkeypatch.setattr("bike_analyzer.backend.api.voice_routes.tempfile.gettempdir", lambda: str(tmp_path))

    resp = client.post("/api/v1/voice/tts", json={"text": "Ciao mondo"})
    assert resp.status_code == 200
    data = resp.json()
    assert "audio_url" in data
    assert data["format"] == "mp3"
    assert data["voice"] == "it-IT-IsabellaNeural"


def test_voice_tts_audio_not_found(client):
    resp = client.get("/api/v1/voice/tts/audio/nonexistent_file.mp3")
    assert resp.status_code == 404


def test_voice_assistant_empty_text(client):
    resp = client.post("/api/v1/voice/assistant", json={"text": ""})
    assert resp.status_code == 400


def test_voice_assistant_no_groq_key(client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    resp = client.post("/api/v1/voice/assistant", json={"text": "ciao"})
    assert resp.status_code in (200, 503)


def test_voice_assistant_with_session_id(client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")

    def fake_chat(messages):
        return "Ciao! Come posso aiutarti?"

    monkeypatch.setattr("bike_analyzer.backend.api.voice_routes._groq_chat_response", fake_chat)

    async def fake_edge_tts(text, voice):
        return b"fake-audio"

    monkeypatch.setattr("bike_analyzer.backend.api.voice_routes._edge_tts", fake_edge_tts)

    resp = client.post("/api/v1/voice/assistant", json={"text": "ciao", "session_id": "session_123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["text"] == "Ciao! Come posso aiutarti?"
    assert data["session_id"] == "session_123"
    assert data["intent"] is not None


def test_detect_intent_navigation():
    assert _detect_intent("apri calendario") == "navigation"
    assert _detect_intent("vai alle uscite") == "navigation"


def test_detect_intent_athlete():
    assert _detect_intent("peso 70 kg") == "athlete_update"
    assert _detect_intent("ftp 250 watt") == "athlete_update"


def test_detect_intent_tracking():
    assert _detect_intent("inizia tracciamento") == "start_tracking"
    assert _detect_intent("ferma tracciamento") == "stop_tracking"


def test_detect_intent_general():
    assert _detect_intent("che tempo fa") == "general"


def test_coach_can_speak_zone_0(client):
    resp = client.post("/api/v1/voice/coach/can-speak", json={"intensity_zone": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_speak"] is True


def test_coach_can_speak_zone_4_blocks(client):
    resp = client.post("/api/v1/voice/coach/can-speak", json={"intensity_zone": 4})
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_speak"] is False
    assert "high intensity" in data["reason"]


def test_coach_speak_returns_text(client):
    resp = client.post(
        "/api/v1/voice/coach/speak",
        json={"category": "recovery", "template_key": "default", "variables": {"power": 120}, "intensity_zone": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["suppressed"] is False
    assert isinstance(data["text"], str)
    assert len(data["text"]) > 0


def test_coach_speak_suppressed_by_zone(client):
    resp = client.post(
        "/api/v1/voice/coach/speak",
        json={"category": "recovery", "template_key": "default", "intensity_zone": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["suppressed"] is True


def test_coach_cues_returns_mapping(client):
    resp = client.get("/api/v1/voice/coach/cues?language=it")
    assert resp.status_code == 200
    data = resp.json()
    assert "cues" in data
    assert isinstance(data["cues"], dict)
    assert len(data["cues"]) > 0


def test_coach_can_speak_zone_0(client):
    resp = client.post("/api/v1/voice/coach/can-speak", json={"intensity_zone": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_speak"] is True


def test_coach_can_speak_zone_4_blocks(client):
    resp = client.post("/api/v1/voice/coach/can-speak", json={"intensity_zone": 4})
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_speak"] is False
    assert "high intensity" in data["reason"]


def test_coach_speak_returns_text(client):
    resp = client.post(
        "/api/v1/voice/coach/speak",
        json={"category": "recovery", "template_key": "default", "variables": {"power": 120}, "intensity_zone": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["suppressed"] is False
    assert isinstance(data["text"], str)
    assert len(data["text"]) > 0


def test_coach_speak_suppressed_by_zone(client):
    resp = client.post(
        "/api/v1/voice/coach/speak",
        json={"category": "recovery", "template_key": "default", "intensity_zone": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["suppressed"] is True


def test_coach_cues_returns_mapping(client):
    resp = client.get("/api/v1/voice/coach/cues?language=it")
    assert resp.status_code == 200
    data = resp.json()
    assert "cues" in data
    assert isinstance(data["cues"], dict)
    assert len(data["cues"]) > 0
