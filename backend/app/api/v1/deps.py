# app/api/v1/deps.py
from fastapi import Depends, Header, HTTPException, Request, status
from app.core.security import decode_access_token
from app.models.user import User

async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
):
    """
    FastAPI dependency to get the current authenticated user.
    
    This dependency extracts and validates the JWT token from either:
    1. Authorization header (Bearer token) - preferred method
    2. HttpOnly cookie (accessToken) - fallback method
    
    Args:
        request: FastAPI Request object (for accessing cookies)
        authorization: Optional Authorization header value
    
    Returns:
        User: The authenticated user object from database
    
    Raises:
        HTTPException (401): If no token is provided (AUTH_REQUIRED)
        HTTPException (401): If token is invalid or expired (AUTH_INVALID_TOKEN)
        HTTPException (401): If user not found in database (AUTH_USER_NOT_FOUND)
    
    Usage:
        Use as a dependency in route handlers:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": str(user.id)}
    """
    token = None
    # 1) Prioritize Authorization: Bearer xxx
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    # 2) Secondly HttpOnly Cookie: accessToken
    if not token:
        token = request.cookies.get("accessToken")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_REQUIRED")

    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_INVALID_TOKEN")

    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_USER_NOT_FOUND")
    return user

async def require_admin(current: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency to ensure the current user is an administrator.
    
    This dependency builds on top of `get_current_user` and adds an additional
    authorization check to verify the user has admin role. Use this for
    admin-only endpoints.
    
    Args:
        current: The authenticated user (from get_current_user dependency)
    
    Returns:
        User: The authenticated admin user object
    
    Raises:
        HTTPException (403): If user is not an admin (FORBIDDEN_ADMIN_ONLY)
        HTTPException (401): If user is not authenticated (from get_current_user)
    
    Usage:
        Use as a dependency in admin route handlers:
        @router.get("/admin/users")
        async def list_users(admin: User = Depends(require_admin)):
            return {"users": [...]}
    """
    if getattr(current, "role", "user") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN_ADMIN_ONLY")
    return current