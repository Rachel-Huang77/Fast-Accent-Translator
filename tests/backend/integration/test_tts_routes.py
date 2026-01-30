import pytest


pytestmark = pytest.mark.asyncio


async def test_melotts_tts_is_streamed(client, monkeypatch):
    captured = {}

    async def fake_melotts(text: str, accent: str):
        captured["text"] = text
        captured["accent"] = accent
        return b"fake-wav", "audio/wav"

    monkeypatch.setattr("app.api.v1.routers.tts._generate_melotts_audio", fake_melotts)

    resp = await client.post(
        "/api/v1/tts/synthesize",
        json={"text": "Testing free voice", "accent": "American English", "model": "free"},
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    assert resp.content == b"fake-wav"
    assert captured == {"text": "Testing free voice", "accent": "American English"}


async def test_elevenlabs_path_is_used_when_paid_model(client, monkeypatch):
    called = {}

    async def fake_elevenlabs(text: str, accent: str):
        called["text"] = text
        called["accent"] = accent
        return b"fake-mp3", "audio/mpeg"

    monkeypatch.setattr("app.api.v1.routers.tts._generate_elevenlabs_audio", fake_elevenlabs)

    resp = await client.post(
        "/api/v1/tts/synthesize",
        json={"text": "Premium voice", "accent": "British English", "model": "paid"},
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert called["accent"] == "British English"


async def test_tts_requires_text(client):
    resp = await client.post("/api/v1/tts/synthesize", json={"text": "", "accent": "us"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Text cannot be empty"


async def test_tts_missing_text_field(client):
    """Test that missing 'text' field returns 422 validation error"""
    resp = await client.post(
        "/api/v1/tts/synthesize",
        json={"accent": "American English", "model": "free"}
    )
    assert resp.status_code == 422
    # Pydantic validation error should contain field information
    error_detail = resp.json()["detail"]
    assert any("text" in str(err).lower() for err in error_detail)


async def test_tts_generation_fails_with_internal_error(client, monkeypatch):
    """Test that TTS generation failure returns 500 error"""
    async def fake_melotts_fails(text: str, accent: str):
        raise RuntimeError("TTS model initialization failed")

    monkeypatch.setattr("app.api.v1.routers.tts._generate_melotts_audio", fake_melotts_fails)

    resp = await client.post(
        "/api/v1/tts/synthesize",
        json={"text": "Test text", "accent": "American English", "model": "free"}
    )

    assert resp.status_code == 500
    error_detail = resp.json()["detail"]
    assert "TTS generation failed" in error_detail
    assert "TTS model initialization failed" in error_detail


async def test_elevenlabs_generation_fails_with_internal_error(client, monkeypatch):
    """Test that ElevenLabs TTS generation failure returns 500 error"""
    async def fake_elevenlabs_fails(text: str, accent: str):
        raise ConnectionError("ElevenLabs API connection failed")

    monkeypatch.setattr("app.api.v1.routers.tts._generate_elevenlabs_audio", fake_elevenlabs_fails)

    resp = await client.post(
        "/api/v1/tts/synthesize",
        json={"text": "Test text", "accent": "British English", "model": "paid"}
    )

    assert resp.status_code == 500
    error_detail = resp.json()["detail"]
    assert "TTS generation failed" in error_detail
    assert "ElevenLabs API connection failed" in error_detail

