# app/schemas/conversation.py
"""
Pydantic schemas for conversation and transcript endpoints.
Defines request/response models for conversation management and transcript retrieval.
"""
from pydantic import BaseModel
from typing import Optional, List

class ConversationItem(BaseModel):
    """
    Conversation item model for list endpoints.
    Represents a single conversation in a paginated list.
    """
    id: str  # Conversation unique identifier
    title: Optional[str] = None  # Conversation title (user-defined or auto-generated)
    accent: str  # Accent type (e.g., "us", "uk")
    model: str  # TTS model used (e.g., "free", "paid")
    startedAt: str  # Conversation start timestamp (ISO format)
    endedAt: Optional[str] = None  # Conversation end timestamp (ISO format, None if ongoing)
    durationSec: Optional[int] = None  # Total conversation duration in seconds

class ConversationListOut(BaseModel):
    """
    Response model for paginated conversation list endpoint.
    Returns a list of conversations with pagination metadata.
    """
    items: List[ConversationItem]  # List of conversation objects
    offset: int  # Pagination offset (number of items skipped)
    limit: int  # Maximum number of items per page
    total: int  # Total number of conversations for the user

class ConversationDetail(BaseModel):
    """
    Detailed conversation model.
    Contains all conversation metadata (same structure as ConversationItem but used in detail context).
    """
    id: str  # Conversation unique identifier
    title: Optional[str] = None  # Conversation title
    accent: str  # Accent type
    model: str  # TTS model used
    startedAt: str  # Conversation start timestamp (ISO format)
    endedAt: Optional[str] = None  # Conversation end timestamp (ISO format)
    durationSec: Optional[int] = None  # Total conversation duration in seconds

class TranscriptOut(BaseModel):
    """
    Transcript segment model.
    Represents a single transcribed segment within a conversation.
    """
    seq: int  # Sequence number (order within conversation)
    isFinal: bool  # Whether this is a final transcript (true) or interim result (false)
    startMs: int | None = None  # Segment start time in milliseconds (relative to conversation start)
    endMs: int | None = None  # Segment end time in milliseconds (relative to conversation start)
    text: str  # Transcribed text content

class ConversationDetailOut(BaseModel):
    """
    Response model for conversation detail endpoint.
    Returns full conversation information including all transcript segments.
    """
    conversation: ConversationDetail  # Conversation metadata
    transcripts: list[TranscriptOut]  # List of transcript segments (ordered by seq)
    audioUrl: str | None = None  # URL to conversation audio file (if available)

class ConversationTitleIn(BaseModel):
    """
    Request model for updating conversation title.
    Used when user renames a conversation.
    """
    title: str  # New conversation title
