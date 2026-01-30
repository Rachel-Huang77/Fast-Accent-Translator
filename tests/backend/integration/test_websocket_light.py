"""
Lightweight WebSocket integration tests.
Tests connection establishment, message format validation, and basic message flow.
Does NOT test full audio processing, ASR transcription, or TTS generation.
"""
import pytest
import json
from fastapi.testclient import TestClient
from app.main import app


class TestWebSocketConnection:
    """Tests for WebSocket connection establishment."""

    def test_ws_upload_accepts_connection(self):
        """WebSocket /ws/upload-audio should accept connections."""
        client = TestClient(app)
        with client.websocket_connect("/ws/upload-audio") as websocket:
            # Connection should be established
            assert websocket is not None

    def test_ws_text_accepts_connection(self):
        """WebSocket /ws/asr-text should accept connections."""
        client = TestClient(app)
        with client.websocket_connect("/ws/asr-text") as websocket:
            assert websocket is not None

    def test_ws_tts_accepts_connection(self):
        """WebSocket /ws/tts-audio should accept connections."""
        client = TestClient(app)
        with client.websocket_connect("/ws/tts-audio") as websocket:
            assert websocket is not None


class TestWebSocketMessageFormat:
    """Tests for WebSocket message format validation."""

    def test_ws_upload_start_message_format(self):
        """WebSocket upload should accept properly formatted start message."""
        client = TestClient(app)
        with client.websocket_connect("/ws/upload-audio") as websocket:
            # Send start message
            start_msg = {
                "type": "start",
                "conversationId": "test-conv-123",
                "accent": "American English",
                "model": "free"
            }
            websocket.send_json(start_msg)
            # Should not raise exception (connection remains open)

    def test_ws_upload_stop_message_format(self):
        """WebSocket upload should accept properly formatted stop message."""
        client = TestClient(app)
        with client.websocket_connect("/ws/upload-audio") as websocket:
            # Send start first
            start_msg = {
                "type": "start",
                "conversationId": "test-conv-456",
                "accent": "American English",
                "model": "free"
            }
            websocket.send_json(start_msg)
            
            # Send stop message
            stop_msg = {
                "type": "stop",
                "webspeech_text": "Test transcription"
            }
            websocket.send_json(stop_msg)
            # Should not raise exception

    def test_ws_upload_invalid_message_type(self):
        """WebSocket upload should handle invalid message type gracefully."""
        client = TestClient(app)
        with client.websocket_connect("/ws/upload-audio") as websocket:
            invalid_msg = {"type": "invalid_type"}
            websocket.send_json(invalid_msg)
            # Should not crash (may close connection or ignore)

    def test_ws_text_subscribe_message_format(self):
        """WebSocket text should accept subscription message."""
        client = TestClient(app)
        with client.websocket_connect("/ws/asr-text") as websocket:
            subscribe_msg = {
                "type": "subscribe",
                "conversationId": "test-conv-789"
            }
            websocket.send_json(subscribe_msg)
            # Should not raise exception


class TestWebSocketBasicFlow:
    """Tests for basic WebSocket message flow."""

    def test_ws_upload_start_stop_flow(self):
        """WebSocket upload should handle start->stop flow."""
        client = TestClient(app)
        with client.websocket_connect("/ws/upload-audio") as websocket:
            # Start
            websocket.send_json({
                "type": "start",
                "conversationId": "test-conv-flow",
                "accent": "American English",
                "model": "free"
            })
            
            # Stop
            websocket.send_json({
                "type": "stop",
                "webspeech_text": "Test"
            })
            
            # Connection should close or remain open without error

    def test_ws_upload_multiple_audio_chunks(self):
        """WebSocket upload should accept multiple binary chunks."""
        client = TestClient(app)
        with client.websocket_connect("/ws/upload-audio") as websocket:
            # Start
            websocket.send_json({
                "type": "start",
                "conversationId": "test-conv-chunks",
                "accent": "American English",
                "model": "free"
            })
            
            # Send multiple binary chunks
            chunk1 = b"fake_audio_chunk_1"
            chunk2 = b"fake_audio_chunk_2"
            websocket.send_bytes(chunk1)
            websocket.send_bytes(chunk2)
            
            # Should not raise exception

