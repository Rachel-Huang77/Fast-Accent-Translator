"""
Unit tests for core.pubsub module.
Tests PubSub channel subscription, unsubscription, and message broadcasting.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.core.pubsub import Channel


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.sent_texts = []
        self.sent_bytes = []

    async def send_text(self, text: str):
        """Mock send_text method."""
        self.sent_texts.append(text)

    async def send_bytes(self, data: bytes):
        """Mock send_bytes method."""
        self.sent_bytes.append(data)


class TestChannelSubscription:
    """Tests for subscription and unsubscription."""

    def test_sub_text_adds_websocket(self):
        """sub_text should add WebSocket to text channel."""
        channel = Channel()
        ws = MockWebSocket()
        conv_id = "conv-123"
        
        # Initially empty
        assert conv_id not in channel._topics["text"]
        
        # Subscribe
        import asyncio
        asyncio.run(channel.sub_text(conv_id, ws))
        
        # Should be subscribed
        assert conv_id in channel._topics["text"]
        assert ws in channel._topics["text"][conv_id]

    def test_sub_text_multiple_websockets_same_conv(self):
        """Multiple WebSockets can subscribe to same conversation."""
        channel = Channel()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        conv_id = "conv-456"
        
        import asyncio
        asyncio.run(channel.sub_text(conv_id, ws1))
        asyncio.run(channel.sub_text(conv_id, ws2))
        
        assert len(channel._topics["text"][conv_id]) == 2
        assert ws1 in channel._topics["text"][conv_id]
        assert ws2 in channel._topics["text"][conv_id]

    def test_sub_text_different_conversations(self):
        """Different conversations maintain separate subscriber sets."""
        channel = Channel()
        ws = MockWebSocket()
        conv1 = "conv-1"
        conv2 = "conv-2"
        
        import asyncio
        asyncio.run(channel.sub_text(conv1, ws))
        asyncio.run(channel.sub_text(conv2, ws))
        
        assert ws in channel._topics["text"][conv1]
        assert ws in channel._topics["text"][conv2]

    def test_unsub_text_removes_websocket(self):
        """unsub_text should remove WebSocket from text channel."""
        channel = Channel()
        ws = MockWebSocket()
        conv_id = "conv-789"
        
        import asyncio
        asyncio.run(channel.sub_text(conv_id, ws))
        assert ws in channel._topics["text"][conv_id]
        
        channel.unsub_text(conv_id, ws)
        assert ws not in channel._topics["text"][conv_id]

    def test_unsub_text_nonexistent_does_not_error(self):
        """unsub_text should not error for non-existent subscription."""
        channel = Channel()
        ws = MockWebSocket()
        conv_id = "conv-nonexistent"
        
        # Should not raise exception
        channel.unsub_text(conv_id, ws)

    def test_sub_tts_adds_websocket(self):
        """sub_tts should add WebSocket to TTS channel."""
        channel = Channel()
        ws = MockWebSocket()
        conv_id = "conv-tts-1"
        
        import asyncio
        asyncio.run(channel.sub_tts(conv_id, ws))
        
        assert conv_id in channel._topics["tts"]
        assert ws in channel._topics["tts"][conv_id]

    def test_unsub_tts_removes_websocket(self):
        """unsub_tts should remove WebSocket from TTS channel."""
        channel = Channel()
        ws = MockWebSocket()
        conv_id = "conv-tts-2"
        
        import asyncio
        asyncio.run(channel.sub_tts(conv_id, ws))
        channel.unsub_tts(conv_id, ws)
        
        assert ws not in channel._topics["tts"].get(conv_id, set())


class TestChannelPublishing:
    """Tests for message publishing."""

    @pytest.mark.asyncio
    async def test_pub_text_sends_to_all_subscribers(self):
        """pub_text should send message to all subscribers."""
        channel = Channel()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        conv_id = "conv-pub-1"
        
        await channel.sub_text(conv_id, ws1)
        await channel.sub_text(conv_id, ws2)
        
        payload = {"type": "update", "text": "Hello"}
        await channel.pub_text(conv_id, payload)
        
        # Both should receive the message
        assert len(ws1.sent_texts) == 1
        assert len(ws2.sent_texts) == 1
        assert json.loads(ws1.sent_texts[0]) == payload
        assert json.loads(ws2.sent_texts[0]) == payload

    @pytest.mark.asyncio
    async def test_pub_text_no_subscribers_no_error(self):
        """pub_text should not error when no subscribers exist."""
        channel = Channel()
        conv_id = "conv-empty"
        
        payload = {"type": "update", "text": "Hello"}
        # Should not raise exception
        await channel.pub_text(conv_id, payload)

    @pytest.mark.asyncio
    async def test_pub_text_only_sends_to_specific_conv(self):
        """pub_text should only send to subscribers of specific conversation."""
        channel = Channel()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        conv1 = "conv-1"
        conv2 = "conv-2"
        
        await channel.sub_text(conv1, ws1)
        await channel.sub_text(conv2, ws2)
        
        payload = {"type": "update", "text": "Hello"}
        await channel.pub_text(conv1, payload)
        
        # Only ws1 should receive
        assert len(ws1.sent_texts) == 1
        assert len(ws2.sent_texts) == 0

    @pytest.mark.asyncio
    async def test_pub_text_handles_disconnected_websocket(self):
        """pub_text should handle disconnected WebSocket gracefully."""
        channel = Channel()
        ws = MockWebSocket()
        conv_id = "conv-disconnect"
        
        await channel.sub_text(conv_id, ws)
        
        # Make send_text raise exception (simulating disconnected)
        async def failing_send_text(text):
            raise Exception("Connection closed")
        ws.send_text = failing_send_text
        
        payload = {"type": "update", "text": "Hello"}
        # Should not raise exception
        await channel.pub_text(conv_id, payload)

    @pytest.mark.asyncio
    async def test_pub_tts_json_sends_to_tts_subscribers(self):
        """pub_tts_json should send to TTS subscribers."""
        channel = Channel()
        ws = MockWebSocket()
        conv_id = "conv-tts-json"
        
        await channel.sub_tts(conv_id, ws)
        
        payload = {"type": "start", "voice": "en-US"}
        await channel.pub_tts_json(conv_id, payload)
        
        assert len(ws.sent_texts) == 1
        assert json.loads(ws.sent_texts[0]) == payload

    @pytest.mark.asyncio
    async def test_pub_tts_bytes_sends_binary_data(self):
        """pub_tts_bytes should send binary data to TTS subscribers."""
        channel = Channel()
        ws = MockWebSocket()
        conv_id = "conv-tts-bytes"
        
        await channel.sub_tts(conv_id, ws)
        
        audio_chunk = b"fake_audio_data_12345"
        await channel.pub_tts_bytes(conv_id, audio_chunk)
        
        assert len(ws.sent_bytes) == 1
        assert ws.sent_bytes[0] == audio_chunk

    @pytest.mark.asyncio
    async def test_pub_tts_bytes_multiple_chunks(self):
        """pub_tts_bytes can send multiple chunks."""
        channel = Channel()
        ws = MockWebSocket()
        conv_id = "conv-tts-multi"
        
        await channel.sub_tts(conv_id, ws)
        
        chunk1 = b"chunk1"
        chunk2 = b"chunk2"
        await channel.pub_tts_bytes(conv_id, chunk1)
        await channel.pub_tts_bytes(conv_id, chunk2)
        
        assert len(ws.sent_bytes) == 2
        assert ws.sent_bytes[0] == chunk1
        assert ws.sent_bytes[1] == chunk2

    @pytest.mark.asyncio
    async def test_pub_tts_bytes_handles_disconnected_websocket(self):
        """pub_tts_bytes should handle disconnected WebSocket gracefully."""
        channel = Channel()
        ws = MockWebSocket()
        conv_id = "conv-tts-disconnect"
        
        await channel.sub_tts(conv_id, ws)
        
        # Make send_bytes raise exception
        async def failing_send_bytes(data):
            raise Exception("Connection closed")
        ws.send_bytes = failing_send_bytes
        
        audio_chunk = b"fake_audio"
        # Should not raise exception
        await channel.pub_tts_bytes(conv_id, audio_chunk)


class TestChannelIsolation:
    """Tests for channel isolation between text and TTS."""

    @pytest.mark.asyncio
    async def test_text_and_tts_channels_are_separate(self):
        """Text and TTS channels should be independent."""
        channel = Channel()
        ws_text = MockWebSocket()
        ws_tts = MockWebSocket()
        conv_id = "conv-mixed"
        
        await channel.sub_text(conv_id, ws_text)
        await channel.sub_tts(conv_id, ws_tts)
        
        # Publish text message
        text_payload = {"type": "text", "data": "Hello"}
        await channel.pub_text(conv_id, text_payload)
        
        # Publish TTS bytes
        audio_chunk = b"audio_data"
        await channel.pub_tts_bytes(conv_id, audio_chunk)
        
        # Text subscriber should only get text
        assert len(ws_text.sent_texts) == 1
        assert len(ws_text.sent_bytes) == 0
        
        # TTS subscriber should only get bytes
        assert len(ws_tts.sent_texts) == 0
        assert len(ws_tts.sent_bytes) == 1

