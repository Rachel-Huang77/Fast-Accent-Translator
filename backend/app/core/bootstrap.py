# app/core/bootstrap.py
"""
Bootstrap module for application initialization.
Handles initial setup tasks such as creating default admin user on first startup.
"""
import os
import logging
from app.models.user import User
from app.core.security import hash_password

logger = logging.getLogger("uvicorn.error")

async def ensure_default_admin() -> None:
    """
    If no admin exists in the database, create a default admin based on environment variables.
    Only takes effect under the following conditions:
      - Currently no user with role="admin"
      - And ADMIN_PASSWORD is set (to avoid using default weak password)
    Environment variables:
      ADMIN_USERNAME (default: "admin")
      ADMIN_EMAIL    (default: "admin@example.com")
      ADMIN_PASSWORD (required, otherwise won't create)
    """
    # Check if any admin user already exists
    has_admin = await User.filter(role="admin").exists()
    if has_admin:
        return  # Skip creation if admin already exists

    # Get admin password from environment (required for security)
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        logger.warning("[bootstrap] No admin present, but ADMIN_PASSWORD not set -> skip creating default admin.")
        return  # Don't create admin without password (security requirement)

    # Get admin credentials from environment variables (with defaults)
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")

    # If username is already taken (user may register a regular account with "admin"), create a non-conflicting name
    base_username = admin_username
    suffix = 1
    while await User.filter(username=admin_username).exists():
        suffix += 1
        admin_username = f"{base_username}{suffix}"  # Append number suffix to make unique

    # Create the default admin user
    u = await User.create(
        username=admin_username,
        email=admin_email,
        password_hash=hash_password(admin_password),  # Hash password before storing
        role="admin",
    )
    logger.warning("[bootstrap] Created default admin -> username=%s email=%s id=%s",
                   u.username, u.email, u.id)
