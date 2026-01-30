# app/schemas/auth.py
"""
Pydantic schemas for authentication endpoints.
Defines request/response models for login and user information.
"""
from pydantic import BaseModel

class LoginRequest(BaseModel):
    """
    Request model for user login endpoint.
    Contains credentials for authentication.
    """
    username: str  # User login name
    password: str  # User password (plain text, will be hashed server-side)

class UserOut(BaseModel):
    """
    User information model returned in authentication responses.
    Contains basic user details without sensitive information.
    """
    id: str  # User unique identifier
    username: str  # User login name
    role: str = "user"  # User role (default: "user", can be "admin")

class LoginResponse(BaseModel):
    """
    Response model for successful login.
    Returns user information and access token for authenticated requests.
    """
    user: UserOut  # User information object
    accessToken: str  # JWT access token for API authentication
