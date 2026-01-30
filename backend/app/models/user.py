# app/models/user.py
"""
Database model for users.
Represents a user account in the system, containing authentication credentials,
profile information, and role-based access control.
"""
import uuid
from tortoise import fields, models

class User(models.Model):
    """
    User database model.
    
    Represents a user account in the system. Each user can have multiple
    conversations and is associated with a role (regular user or administrator).
    
    Relationships:
    - Has many Conversations (one-to-many, via related_name="conversations")
    - Has many LicenseKeys (one-to-many, via used_by foreign key in LicenseKey model)
    
    Security:
    - Password is stored as a hash (never store plain text passwords)
    - Username must be unique across all users
    - Role determines access level (user vs admin)
    """
    id = fields.UUIDField(pk=True, default=uuid.uuid4)  # Primary key: unique user identifier
    username = fields.CharField(
        max_length=256, 
        unique=True, 
        index=True
    )  # User login name (must be unique, indexed for fast lookups)
    email = fields.CharField(max_length=256, null=True)  # User email address (optional, can be null)
    password_hash = fields.CharField(max_length=255)  # Hashed password (using argon2 or bcrypt, never store plain text)
    role = fields.CharField(max_length=16, default="user")  # User role: "user" (default) or "admin" (administrator)
    created_at = fields.DatetimeField(auto_now_add=True)  # Timestamp when account was created (auto-set on creation)

    class Meta:
        """Tortoise ORM metadata configuration."""
        table = "users"  # Database table name
