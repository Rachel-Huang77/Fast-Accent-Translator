# app/models/__init__.py
"""
Database models module initialization.
Exports all database models for convenient imports throughout the application.

This module provides a centralized location for importing all Tortoise ORM models,
making it easier to use models in other parts of the application without
needing to know the exact file structure.

Models exported:
- User: User account and authentication model
- Conversation: Conversation session model
- Transcript: Transcript segment model (belongs to Conversation)
- LicenseKey: License key model for access control
"""
from .user import User
from .conversation import Conversation
from .transcript import Transcript
from .license_key import LicenseKey
