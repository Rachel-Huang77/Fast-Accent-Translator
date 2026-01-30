# app/models/conversation.py
"""
Database model for conversations.
Represents a single conversation session between a user and the system,
containing metadata about the conversation (accent, model, timestamps, etc.)
and linking to associated transcript segments.
"""
import uuid
from tortoise import fields, models

class Conversation(models.Model):
    """
    Conversation database model.
    
    A conversation represents a single session where a user interacts with the system
    for speech recognition and translation. Each conversation can contain multiple
    transcript segments and is associated with a specific user.
    
    Relationships:
    - Belongs to a User (many-to-one)
    - Has many Transcript segments (one-to-many, via related_name in Transcript model)
    """
    id = fields.UUIDField(pk=True, default=uuid.uuid4)  # Primary key: unique conversation identifier
    user = fields.ForeignKeyField(
        "models.User", 
        related_name="conversations", 
        on_delete=fields.CASCADE
    )  # Foreign key to User model; cascade delete (if user is deleted, conversations are deleted)
    title = fields.CharField(max_length=128, null=True)  # User-defined or auto-generated conversation title
    accent = fields.CharField(max_length=8)  # Accent type (e.g., "us", "uk") - Sprint1: only 'us' supported
    model = fields.CharField(max_length=16, default="free")  # TTS model used: "free" (MelonTTS) or "paid" (ElevenLabs)
    started_at = fields.DatetimeField(auto_now_add=True)  # Timestamp when conversation was created (auto-set on creation)
    ended_at = fields.DatetimeField(null=True)  # Timestamp when conversation ended (null if still ongoing)
    duration_sec = fields.IntField(null=True)  # Total conversation duration in seconds (calculated after conversation ends)

    class Meta:
        """Tortoise ORM metadata configuration."""
        table = "conversations"  # Database table name
