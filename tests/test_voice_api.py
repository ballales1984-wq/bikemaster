"""Voice API routes tests."""

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
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


def test_voice_stt_no_file(client):
    resp = client.post("/api/v1/voice/stt")
    assert resp.status_code == 422


def test_voice_tts_empty_text(client):
    resp = client.post("/api/v1/voice/tts", json={"text": ""})
    assert resp.status_code == 400


def test_voice_assistant_empty_text(client):
    resp = client.post("/api/v1/voice/assistant", json={"text": ""})
    assert resp.status_code == 400


def test_voice_assistant_no_groq_key(client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    resp = client.post("/api/v1/voice/assistant", json={"text": "ciao"})
    assert resp.status_code in (200, 503)
