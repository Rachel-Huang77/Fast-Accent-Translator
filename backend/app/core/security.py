# app/core/security.py
"""
Security module for authentication and authorization.
Handles password hashing, JWT token creation/validation, and cryptographic operations.
"""
import os
import datetime as dt
import jwt  # PyJWT
from passlib.context import CryptContext
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from project root
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Password hashing context
# Only use argon2, completely bypass bcrypt (most convenient during development)
# Argon2 is a modern, secure password hashing algorithm
pwd_context = CryptContext(
    schemes=["argon2"],  # Use Argon2 for password hashing
    deprecated="auto",   # Automatically handle deprecated schemes
)

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")  # Secret key for JWT signing (use strong secret in production)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))  # Token expiration time in minutes
JWT_ALG = "HS256"  # JWT signing algorithm (HMAC SHA-256)

def hash_password(plain: str) -> str:
    """
    Hash a plain text password using Argon2.
    
    Args:
        plain: Plain text password to hash
    
    Returns:
        Hashed password string (safe to store in database)
    
    Note: Never store plain text passwords. Always use this function before saving.
    """
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain text password against a hashed password.
    
    Args:
        plain: Plain text password to verify
        hashed: Hashed password from database
    
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: str, role: str) -> str:
    """
    Create a JWT access token for user authentication.
    
    The token includes user ID and role for quick RBAC (Role-Based Access Control)
    determination at the gateway/API layer without additional database queries.
    
    Args:
        user_id: Unique user identifier (UUID string)
        role: User role ("user" or "admin")
    
    Returns:
        Encoded JWT token string
    
    Token payload includes:
        - sub: Subject (user ID)
        - role: User role for authorization
        - iat: Issued at timestamp
        - exp: Expiration timestamp
    """
    now = dt.datetime.utcnow()
    payload = {
        "sub": user_id,  # Subject (user ID)
        "role": role,    # User role for RBAC
        "iat": now,      # Issued at timestamp
        "exp": now + dt.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),  # Expiration timestamp
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: JWT token string to decode
    
    Returns:
        Decoded token payload dictionary containing user_id, role, etc.
    
    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid or malformed
    
    Note: This function validates the token signature and expiration automatically.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
