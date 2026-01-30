# app/schemas/key.py
"""
Pydantic schemas for license key verification endpoints.
Defines request/response models for key validation operations.
"""
from pydantic import BaseModel
from typing import Optional

class VerifyKeyIn(BaseModel):
    """
    Request model for license key verification.
    Contains the plain text key entered by the user.
    """
    key: str  # User input plain text key (will be hashed server-side for comparison)

class VerifyKeyOut(BaseModel):
    """
    Response model for license key verification.
    Indicates whether the key is valid and optionally provides a message.
    """
    ok: bool  # True if key is valid and can be used, False otherwise
    message: Optional[str] = None  # Optional message explaining the verification result
