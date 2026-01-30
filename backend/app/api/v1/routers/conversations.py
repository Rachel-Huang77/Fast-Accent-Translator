import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.transcript import Transcript

router = APIRouter(prefix="/conversations", tags=["conversations"])

# ===== Schemas =====
class ConversationTitleIn(BaseModel):
    title: str

class CreateConversationIn(BaseModel):
    title: str | None = None

class AppendSegmentIn(BaseModel):
    startMs: int | None = None
    endMs: int | None = None
    text: str
    audioUrl: str | None = None

# ===== Routes =====
@router.get("", response_model=dict)
async def list_conversations(
    user: User = Depends(get_current_user),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """
    Get paginated list of conversations for the authenticated user.
    
    Returns a list of conversations ordered by start time (newest first),
    with pagination support. Only returns conversations belonging to the
    authenticated user.
    
    Args:
        user: Authenticated user (from dependency)
        offset: Number of items to skip (for pagination)
        limit: Maximum number of items to return (1-200)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with:
                - items: List of conversation objects
                - offset: Current pagination offset
                - limit: Current page size
                - total: Total number of conversations for the user
    
    Raises:
        HTTPException (401): If user is not authenticated
    """
    total = await Conversation.filter(user=user).count()
    rows = await Conversation.filter(user=user).order_by("-started_at").offset(offset).limit(limit)
    items = []
    for c in rows:
        items.append({
            "id": str(c.id),
            "title": c.title,
            "accent": c.accent,
            "model": c.model,
            "startedAt": c.started_at.isoformat() + "Z",
            "endedAt": c.ended_at.isoformat() + "Z" if c.ended_at else None,
            "durationSec": c.duration_sec,
        })
    return {"success": True, "data": {"items": items, "offset": offset, "limit": limit, "total": total}}

@router.post("", response_model=dict)
async def create_conversation(body: CreateConversationIn, user: User = Depends(get_current_user)):
    """
    Create a new conversation for the authenticated user.
    
    Creates a new conversation with default settings (accent="us", model="free").
    The conversation title is optional and can be set later.
    
    Args:
        body: Request body containing optional title
        user: Authenticated user (from dependency)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with:
                - id: str (conversation UUID)
                - title: str (conversation title, empty string if not provided)
                - createdAtMs: int (creation timestamp in milliseconds)
    
    Raises:
        HTTPException (401): If user is not authenticated
    """
    now = dt.datetime.utcnow()
    c = await Conversation.create(
        user=user,
        accent="us",
        model="free",
        started_at=now,
        title=(body.title.strip() if body.title else None),
    )
    return {"success": True, "data": {"id": str(c.id), "title": c.title or "", "createdAtMs": int(now.timestamp()*1000)}}

@router.get("/{cid}", response_model=dict)
async def get_conversation_detail(cid: str, user: User = Depends(get_current_user)):
    """
    Get detailed information about a specific conversation.
    
    Returns full conversation metadata including all transcript segments.
    Only returns conversations belonging to the authenticated user.
    
    Args:
        cid: Conversation ID (UUID string)
        user: Authenticated user (from dependency)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with:
                - conversation: Conversation metadata object
                - transcripts: List of transcript segments (ordered by seq)
                - audioUrl: str | None (audio file URL if available)
    
    Raises:
        HTTPException (401): If user is not authenticated
        HTTPException (404): If conversation not found or doesn't belong to user
    """
    c = await Conversation.get_or_none(id=cid, user=user)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")
    trs = await Transcript.filter(conversation_id=c.id).order_by("seq")
    transcripts = [{
        "seq": t.seq,
        "isFinal": t.is_final,
        "startMs": t.start_ms,
        "endMs": t.end_ms,
        "text": t.text,
        "audioUrl": t.audio_url,
        "speakerId": t.speaker_id,  # ✅ Return speaker ID
    } for t in trs]
    return {
        "success": True,
        "data": {
            "conversation": {
                "id": str(c.id),
                "title": c.title,
                "accent": c.accent,
                "model": c.model,
                "startedAt": c.started_at.isoformat() + "Z",
                "endedAt": c.ended_at.isoformat() + "Z" if c.ended_at else None,
                "durationSec": c.duration_sec,
            },
            "transcripts": transcripts,
            "audioUrl": None,
        }
    }

@router.patch("/{cid}", response_model=dict)
async def rename_conversation(cid: str, body: ConversationTitleIn, user: User = Depends(get_current_user)):
    """
    Update the title of a conversation.
    
    Allows users to rename their conversations. Title is trimmed and limited
    to 80 characters. Only conversations belonging to the authenticated user
    can be renamed.
    
    Args:
        cid: Conversation ID (UUID string)
        body: Request body containing new title
        user: Authenticated user (from dependency)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with:
                - id: str (conversation UUID)
                - title: str (updated title)
    
    Raises:
        HTTPException (401): If user is not authenticated
        HTTPException (404): If conversation not found or doesn't belong to user
    """
    c = await Conversation.get_or_none(id=cid, user=user)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")
    c.title = (body.title or "").strip()[:80]
    await c.save()
    return {"success": True, "data": {"id": str(c.id), "title": c.title}}

@router.delete("/{cid}", response_model=dict)
async def delete_conversation(cid: str, user: User = Depends(get_current_user)):
    """
    Delete a conversation and all its transcript segments.
    
    Permanently deletes a conversation and all associated transcripts.
    Only conversations belonging to the authenticated user can be deleted.
    Transcripts are deleted first (explicitly) before the conversation.
    
    Args:
        cid: Conversation ID (UUID string)
        user: Authenticated user (from dependency)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with:
                - id: str (deleted conversation UUID)
                - deleted: bool (always True)
    
    Raises:
        HTTPException (401): If user is not authenticated
        HTTPException (404): If conversation not found or doesn't belong to user
    """
    c = await Conversation.get_or_none(id=cid, user=user)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")
    # Delete transcripts first, then conversation (foreign key cascades, but manual is clearer)
    await Transcript.filter(conversation_id=c.id).delete()
    await c.delete()
    return {"success": True, "data": {"id": cid, "deleted": True}}

@router.post("/{cid}/segments", response_model=dict)
async def append_segment(cid: str, body: AppendSegmentIn, user: User = Depends(get_current_user)):
    """
    Append a new transcript segment to a conversation.
    
    Creates a new transcript segment with the provided text and timestamps.
    The segment sequence number is automatically assigned based on existing
    segments in the conversation.
    
    Args:
        cid: Conversation ID (UUID string)
        body: Request body containing segment data:
            - startMs: int | None (segment start time in milliseconds)
            - endMs: int | None (segment end time in milliseconds)
            - text: str (transcribed text content)
            - audioUrl: str | None (optional audio file URL)
        user: Authenticated user (from dependency)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with segment information:
                - id: str (segment identifier, format: "s_{seq}")
                - seq: int (sequence number)
                - startMs: int | None
                - endMs: int | None
                - text: str
                - audioUrl: str | None
    
    Raises:
        HTTPException (401): If user is not authenticated
        HTTPException (404): If conversation not found or doesn't belong to user
    """
    c = await Conversation.get_or_none(id=cid, user=user)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")
    seq = await Transcript.filter(conversation_id=c.id).count() + 1
    t = await Transcript.create(
        conversation_id=c.id,
        seq=seq,
        is_final=True,
        start_ms=body.startMs,
        end_ms=body.endMs,
        text=body.text,
        audio_url=body.audioUrl,
    )
    return {"success": True, "data": {"id": f"s_{seq}", "seq": seq, "startMs": t.start_ms, "endMs": t.end_ms, "text": t.text, "audioUrl": t.audio_url}}
