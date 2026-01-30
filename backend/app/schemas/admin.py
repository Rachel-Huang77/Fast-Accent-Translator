# app/schemas/admin.py
"""
Pydantic schemas for admin user management endpoints.
Defines request/response models for user CRUD operations and password reset.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# ========== Common return model ==========
class AdminUserBase(BaseModel):
    """
    Base user model for admin endpoints.
    Represents user information returned in admin API responses.
    """
    id: str  # User unique identifier
    username: str  # User login name
    email: Optional[str] = None  # User email address (optional)
    role: Literal["user", "admin"]  # User role: regular user or administrator
    createdAt: str = Field(alias="created_at")  # Account creation timestamp (ISO format)

    class Config:
        """Pydantic configuration: allow both field name and alias for population."""
        populate_by_name = True


class AdminUserListOut(BaseModel):
    """
    Response model for paginated user list endpoint.
    Returns a list of users with pagination metadata.
    """
    items: List[AdminUserBase]  # List of user objects
    offset: int  # Pagination offset (number of items skipped)
    limit: int  # Maximum number of items per page
    total: int  # Total number of users matching the query


class AdminUserDetailOut(BaseModel):
    """
    Response model for single user detail endpoint.
    Returns detailed information about a specific user.
    """
    user: AdminUserBase  # User object with all details


# ========== Input model ==========
class AdminUserUpdateIn(BaseModel):
    """
    Request model for updating user information.
    All fields are optional - only provided fields will be updated.
    """
    username: Optional[str] = None  # New username (must be unique if provided)
    email: Optional[str] = None  # New email address (must be unique if provided)
    role: Optional[Literal["user", "admin"]] = None  # New role (cannot demote last admin)


class AdminResetPasswordIn(BaseModel):
    """
    Request model for admin-initiated password reset.
    Used when admin resets a user's password.
    """
    newPassword: str = Field(min_length=6)  # New password (minimum 6 characters)
