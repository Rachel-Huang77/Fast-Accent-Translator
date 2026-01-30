# app/schemas/license_key.py
"""
Pydantic schemas for license key management endpoints.
Defines request/response models for batch key generation and verification.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, constr
from typing import List, Optional

class BatchGenerateIn(BaseModel):
    """
    Request model for batch license key generation.
    Used by admins to generate multiple license keys at once.
    """
    count: int = Field(ge=1, le=200, description="Number of keys to generate, maximum 200")
    keyType: constr(strip_whitespace=True, min_length=1, max_length=16) = "paid"  # Key type (e.g., "paid", "trial")
    expireDays: Optional[int] = Field(default=None, ge=1, le=3650, description="Days until expiration; None means no expiration")
    prefix: Optional[constr(strip_whitespace=True, min_length=1, max_length=8)] = Field(
        default="FAT", description="Key prefix for identifying channel/environment"
    )  # Prefix for key format (e.g., "FAT-XXXX-XXXX-XXXX-XXXX")

class GeneratedKeyItem(BaseModel):
    """
    Model for a single generated license key.
    Returned in batch generation response (only time plaintext key is exposed).
    """
    id: str  # Database ID of the generated key
    key: str  # Plain text license key (only returned during generation, not stored in DB)
    keyType: str  # Key type (e.g., "paid", "trial")
    expiresAt: Optional[str] = None  # Expiration timestamp (ISO format, None if no expiration)

class BatchGenerateOut(BaseModel):
    """
    Response model for batch key generation endpoint.
    Returns list of generated keys with their metadata.
    """
    keys: List[GeneratedKeyItem]  # List of generated key objects (includes plaintext keys)

class VerifyKeyIn(BaseModel):
    """
    Request model for license key verification with optional consumption.
    Used when user verifies or redeems a license key.
    """
    key: str  # Plain text license key to verify
    consume: bool = False  # If True, mark key as used after verification; if False, only check validity
