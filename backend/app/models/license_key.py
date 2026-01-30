# app/models/license_key.py
import uuid
import hashlib
from typing import Optional
from tortoise import fields, models

class LicenseKey(models.Model):
    """
    Purchase / upgrade redemption key.
    - key_hash: sha256(plain text key) 64-character hexadecimal string, unique (plain text not stored)
    - prefix: Plain text key prefix (e.g., FAT)
    - suffix_last4: Last 4 characters of plain text key (e.g., 3F9C)
    - expires_at: Expiration time (optional)
    - is_used: Whether already redeemed
    - used_by: Redeemer (User foreign key, can be null)
    - used_at: Redemption time
    - created_at: Creation time
    """
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    key_hash = fields.CharField(max_length=64, unique=True, index=True)
    key_type = fields.CharField(max_length=16, default="paid")  # Reserved types: paid / trial / etc

    # ⭐ New: Only for display, not the complete key
    prefix = fields.CharField(max_length=8, null=True)
    suffix_last4 = fields.CharField(max_length=4, null=True)

    expires_at = fields.DatetimeField(null=True)
    is_used = fields.BooleanField(default=False)

    used_by: Optional[fields.ForeignKeyNullableRelation["User"]] = fields.ForeignKeyField(
        "models.User", related_name="license_keys", null=True
    )
    used_at = fields.DatetimeField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "license_keys"

    @staticmethod
    def sha256_hex(raw: str) -> str:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
