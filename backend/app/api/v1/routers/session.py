# app/api/v1/routers/session.py
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.api.v1.deps import get_current_user
from app.models.conversation import Conversation
from app.models.user import User

router = APIRouter(prefix="/session", tags=["session"])

class CreateSessionIn(BaseModel):
    accent: str = Field(pattern="^(us)$")  # S1 only us

@router.post("")
async def create_session(body: CreateSessionIn, user: User = Depends(get_current_user)):
    """
    Create a new conversation session.
    
    Creates a new conversation for the authenticated user with the specified
    accent and default TTS model. This endpoint is used to initialize a new
    conversation before starting audio recording.
    
    Args:
        body: Request body containing accent preference
        user: Authenticated user (from dependency)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with session information:
                - sessionId: str (conversation UUID)
                - accent: str (accent code, currently only "us")
                - model: str (TTS model, default "free")
                - createdAt: str (ISO timestamp with Z suffix)
    
    Raises:
        HTTPException (400): If accent is not "us" (only supported in Sprint 1)
        HTTPException (401): If user is not authenticated
    
    Note:
        Currently only supports "us" accent. Other accents will be added in future sprints.
    """
    if body.accent != "us":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only 'us' supported in Sprint 1")
    conv = await Conversation.create(
        user=user,
        accent="us",
        model="free",
        started_at=dt.datetime.utcnow(),
        title=None,
    )
    return {"success": True,
            "data": {"sessionId": str(conv.id), "accent": "us", "model": "free",
                     "createdAt": conv.started_at.isoformat() + "Z"}}
