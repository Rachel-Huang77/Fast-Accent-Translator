# app/models/transcript.py
import uuid
from tortoise import fields, models

class Transcript(models.Model):
    id = fields.IntField(pk=True)  # Or UUID, depending on your current definition
    conversation = fields.ForeignKeyField("models.Conversation", related_name="transcripts")

    seq = fields.IntField()              # Segment sequence number, int4 is sufficient
    is_final = fields.BooleanField()

    # ↓↓↓ Changed IntField to BigIntField (supports millisecond-level timestamps)
    start_ms = fields.BigIntField(null=True)
    end_ms   = fields.BigIntField(null=True)

    text = fields.TextField()
    audio_url = fields.CharField(max_length=1024, null=True)

    # New: Speaker ID ("SPEAKER_00", "SPEAKER_01", "SPEAKER_02")
    speaker_id = fields.CharField(max_length=32, null=True)
    
    class Meta:
        table = "transcripts"