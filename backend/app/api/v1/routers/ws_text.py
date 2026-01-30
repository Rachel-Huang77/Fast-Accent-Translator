from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
import json
from app.core.pubsub import channel

router = APIRouter()

@router.websocket("/ws/asr-text")
async def ws_asr_text(ws: WebSocket):
    """
    WebSocket endpoint for subscribing to ASR text message updates.
    
    This endpoint allows clients to subscribe to real-time transcript updates
    for a specific conversation. Clients send a "subscribe" message with a
    conversation ID, and then receive text updates via the PubSub channel.
    
    Message flow:
    1. Client connects to WebSocket
    2. Client sends: {"type": "subscribe", "conversationId": "..."}
    3. Server subscribes client to conversation's text channel
    4. Server sends: {"type": "ready", "conversationId": "..."}
    5. Server broadcasts transcript updates to all subscribers
    
    Args:
        ws: WebSocket connection object
    
    Note:
        The WebSocket connection remains open to receive real-time updates.
        Clients are automatically unsubscribed when the connection closes.
    """
    await ws.accept()
    print("[ws_text] connected")
    conv_id = None
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            if msg.get("type") == "subscribe":
                conv_id = msg.get("conversationId")
                await channel.sub_text(conv_id, ws)
                print("[ws_text] subscribed", conv_id)
                # Return ready
                await ws.send_text(json.dumps({"type": "ready", "conversationId": conv_id}))
    except WebSocketDisconnect:
        if conv_id:
            channel.unsub_text(conv_id, ws)
        print("[ws_text] disconnected")
    except Exception as e:
        if conv_id:
            channel.unsub_text(conv_id, ws)
        print("[ws_text] error:", repr(e))
