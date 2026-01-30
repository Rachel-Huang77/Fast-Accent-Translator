# backend/app/core/pubsub.py
"""
PubSub (Publish-Subscribe) module for WebSocket message broadcasting.
Provides a simple channel-based messaging system for real-time communication
between backend services and frontend clients via WebSocket connections.
"""
from typing import Dict, Set
from starlette.websockets import WebSocket
import json

class Channel:
    """
    Simple PubSub channel implementation for WebSocket message broadcasting.
    
    Supports two types of channels:
      - text: Send JSON text messages (e.g., transcript updates)
      - tts: Send JSON control messages + binary audio chunks (e.g., TTS audio streaming)
    
    Architecture:
    - Router is responsible for ws.accept(); this module only handles message routing
    - Messages are broadcast to all subscribers of a specific conversation ID
    - Subscribers are automatically cleaned up when WebSocket connections close
    
    Data structure:
    - _topics: Dict[topic_name, Dict[conversation_id, Set[WebSocket]]]
    """
    def __init__(self):
        """
        Initialize the PubSub channel with empty topic dictionaries.
        Creates separate channels for "text" and "tts" message types.
        """
        # Data structure: topic -> conv_id -> set(WebSocket)
        # Example: {"text": {"conv-123": {ws1, ws2}, "conv-456": {ws3}}}
        self._topics: Dict[str, Dict[str, Set[WebSocket]]] = {
            "text": {},  # Channel for text messages (transcripts, updates)
            "tts": {},   # Channel for TTS audio streaming
        }

    # -------- subscribe / unsubscribe (no accept, only register) --------
    async def sub_text(self, conv_id: str, ws: WebSocket):
        """
        Subscribe a WebSocket connection to text messages for a specific conversation.
        
        Args:
            conv_id: Conversation ID to subscribe to
            ws: WebSocket connection to register
        """
        self._topics["text"].setdefault(conv_id, set()).add(ws)

    def unsub_text(self, conv_id: str, ws: WebSocket):
        """
        Unsubscribe a WebSocket connection from text messages for a specific conversation.
        
        Args:
            conv_id: Conversation ID to unsubscribe from
            ws: WebSocket connection to remove
        """
        self._topics["text"].get(conv_id, set()).discard(ws)

    async def sub_tts(self, conv_id: str, ws: WebSocket):
        """
        Subscribe a WebSocket connection to TTS audio messages for a specific conversation.
        
        Args:
            conv_id: Conversation ID to subscribe to
            ws: WebSocket connection to register
        """
        self._topics["tts"].setdefault(conv_id, set()).add(ws)

    def unsub_tts(self, conv_id: str, ws: WebSocket):
        """
        Unsubscribe a WebSocket connection from TTS audio messages for a specific conversation.
        
        Args:
            conv_id: Conversation ID to unsubscribe from
            ws: WebSocket connection to remove
        """
        self._topics["tts"].get(conv_id, set()).discard(ws)

    # -------- publish --------
    async def pub_text(self, conv_id: str, payload: dict):
        """
        Publish a JSON text message to all subscribers of a conversation.
        
        Args:
            conv_id: Conversation ID to publish to
            payload: Dictionary payload to send (will be JSON-encoded)
        
        Note: Silently ignores errors from disconnected WebSocket connections.
        """
        conns = list(self._topics["text"].get(conv_id, set()))  # Get all subscribers for this conversation
        msg = json.dumps(payload)  # Serialize payload to JSON string
        for s in conns:
            try:
                await s.send_text(msg)
            except Exception:
                pass  # Ignore errors (connection may be closed)

    async def pub_tts_json(self, conv_id: str, payload: dict):
        """
        Publish a JSON control message to TTS subscribers of a conversation.
        Used for TTS control messages (e.g., start, stop, metadata).
        
        Args:
            conv_id: Conversation ID to publish to
            payload: Dictionary payload to send (will be JSON-encoded)
        
        Note: Silently ignores errors from disconnected WebSocket connections.
        """
        conns = list(self._topics["tts"].get(conv_id, set()))  # Get all TTS subscribers
        msg = json.dumps(payload)  # Serialize payload to JSON string
        for s in conns:
            try:
                await s.send_text(msg)
            except Exception:
                pass  # Ignore errors (connection may be closed)

    async def pub_tts_bytes(self, conv_id: str, chunk: bytes):
        """
        Publish binary audio data to TTS subscribers of a conversation.
        Used for streaming TTS audio chunks.
        
        Args:
            conv_id: Conversation ID to publish to
            chunk: Binary audio data to send
        
        Note: Silently ignores errors from disconnected WebSocket connections.
        """
        conns = list(self._topics["tts"].get(conv_id, set()))  # Get all TTS subscribers
        for s in conns:
            try:
                await s.send_bytes(chunk)  # Send binary data directly
            except Exception:
                pass  # Ignore errors (connection may be closed)

# Global channel instance (singleton pattern)
# Import this instance in other modules to publish/subscribe messages
channel = Channel()
