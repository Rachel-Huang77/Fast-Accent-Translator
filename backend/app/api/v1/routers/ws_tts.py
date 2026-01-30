# backend/app/routers/ws_tts.py
from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
import json
from app.core.pubsub import channel

router = APIRouter()

@router.websocket("/ws/tts-audio")
async def ws_tts(ws: WebSocket):
    """
    WebSocket endpoint for subscribing to TTS audio streaming.
    
    This endpoint allows clients to subscribe to real-time TTS audio chunks
    for a specific conversation. Clients send a "start" message with a
    conversation ID, and then receive audio data (both JSON control messages
    and binary audio chunks) via the PubSub channel.
    
    Message flow:
    1. Client connects to WebSocket
    2. Client sends: {"type": "start", "conversationId": "..."}
    3. Server subscribes client to conversation's TTS channel
    4. Server sends: {"type": "ready", "conversationId": "..."}
    5. Server streams TTS audio chunks (JSON + binary) to all subscribers
    
    Args:
        ws: WebSocket connection object
    
    Note:
        The WebSocket connection remains open to receive audio streams.
        Clients are automatically unsubscribed when the connection closes.
    """
    await ws.accept()                     # ← Router handles accept uniformly
    print("[ws_tts] connected")
    conv_id = None
    try:
        while True:
            raw = await ws.receive_text() # Can only receive after accept
            msg = json.loads(raw)
            if msg.get("type") == "start":
                conv_id = msg.get("conversationId")
                await channel.sub_tts(conv_id, ws)    # Only register here
                print("[ws_tts] subscribed", conv_id)
                await ws.send_text(json.dumps({"type": "ready", "conversationId": conv_id}))
    except WebSocketDisconnect:
        if conv_id:
            channel.unsub_tts(conv_id, ws)
        print("[ws_tts] disconnected")
    except Exception as e:
        if conv_id:
            channel.unsub_tts(conv_id, ws)
        print("[ws_tts] error:", repr(e))
