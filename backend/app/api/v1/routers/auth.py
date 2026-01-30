# app/api/v1/routers/auth.py
from fastapi import APIRouter, HTTPException, Response, status, Depends
from pydantic import BaseModel
from app.core.security import verify_password, create_access_token, hash_password
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterIn(BaseModel):
    username: str
    email: str | None = None
    password: str

class CheckResetIn(BaseModel):
    username: str
    email: str

class ResetPasswordIn(BaseModel):
    userId: str
    newPassword: str

class ChangePasswordIn(BaseModel):
    newPassword: str

@router.post("/register")
async def register(body: RegisterIn):
    """
    Register a new user account.
    
    Creates a new user account with the provided username, email (optional),
    and password. The password is hashed before storage. Username and email
    must be unique across all users.
    
    Args:
        body: Request body containing:
            - username: str (must be unique)
            - email: str | None (optional, must be unique if provided)
            - password: str (will be hashed before storage)
    
    Returns:
        dict: Success response with user data, or error response:
            - success: bool
            - data: dict with user id, username, email (if success)
            - error: dict with error code and message (if failure)
    
    Error codes:
        - BAD_REQUEST: Missing username or password
        - USERNAME_EXISTS: Username already taken
        - EMAIL_EXISTS: Email already registered
    """
    # Basic validation, avoid pydantic error becoming 500
    if not body.username or not body.password:
        return {"success": False, "error": {"code": "BAD_REQUEST", "message": "username/password required"}}
    # Check duplicates
    if await User.get_or_none(username=body.username):
        return {"success": False, "error": {"code": "USERNAME_EXISTS", "message": "Username already exists"}}
    if body.email and await User.get_or_none(email=body.email):
        return {"success": False, "error": {"code": "EMAIL_EXISTS", "message": "Email already registered"}}
    # Create
    u = await User.create(
        username=body.username,
        email=(body.email or None),
        password_hash=hash_password(body.password),
        role="user",
    )
    return {"success": True, "data": {"id": str(u.id), "username": u.username, "email": u.email}}

@router.post("/login")
async def login(payload: LoginRequest, response: Response):
    """
    Authenticate user and create access token.
    
    Validates user credentials and creates a JWT access token upon successful
    authentication. The token is returned in the response body and also set
    as an HttpOnly cookie for browser-based clients.
    
    Args:
        payload: Request body containing username and password
        response: FastAPI Response object (for setting cookies)
    
    Returns:
        dict: Response containing:
            - success: bool (always True on success)
            - data: dict with:
                - user: User information (id, username, email, role)
                - accessToken: JWT token string
    
    Raises:
        HTTPException (401): If credentials are invalid
    
    Note:
        The access token is also set as an HttpOnly cookie named "accessToken"
        for automatic inclusion in subsequent requests.
    """
    user = await User.get_or_none(username=payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"code":"AUTH_INVALID_CREDENTIALS","message":"Incorrect username or password"})
    token = create_access_token(str(user.id), user.role)
    response.set_cookie("accessToken", token, httponly=True, secure=False, samesite="lax")
    return {"success": True, "data": {"user": {"id": str(user.id), "username": user.username, "email": user.email, "role": user.role},
                                      "accessToken": token}}

@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Returns the user information for the currently authenticated user based
    on the JWT token in the request.
    
    Args:
        user: Authenticated user (from dependency)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with user information:
                - id: str (user UUID)
                - username: str
                - email: str
                - role: str ("user" or "admin")
    
    Raises:
        HTTPException (401): If user is not authenticated
    """
    return {"success": True, "data": {"id": str(user.id), "username": user.username, "email": user.email, "role": user.role}}

@router.post("/logout")
async def logout(response: Response):
    """
    Log out the current user by clearing the access token cookie.
    
    Removes the HttpOnly "accessToken" cookie from the client. This endpoint
    always returns success, even if no cookie was present.
    
    Args:
        response: FastAPI Response object (for deleting cookies)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
    
    Note:
        This endpoint only clears the cookie. The JWT token itself remains
        valid until it expires. For complete invalidation, implement token
        blacklisting on the backend.
    """
    response.delete_cookie("accessToken")
    return {"success": True}

@router.post("/check-reset")
async def check_reset(body: CheckResetIn):
    """
    Verify username and email for password reset eligibility.
    
    Checks if a user exists with the provided username and email combination.
    This is the first step in the password reset flow - it verifies the user's
    identity before allowing password reset.
    
    Args:
        body: Request body containing:
            - username: str
            - email: str
    
    Returns:
        dict: Response containing:
            - success: bool
            - data: dict with userId if user found (if success)
            - error: dict with error code and message if user not found (if failure)
    
    Error codes:
        - USER_NOT_FOUND: No user found with matching username and email
    """
    u = await User.get_or_none(username=body.username)
    if not u or (u.email or "").lower() != (body.email or "").lower():
        return {"success": False, "error": {"code": "USER_NOT_FOUND", "message": "User not found"}}
    return {"success": True, "data": {"userId": str(u.id)}}

@router.post("/reset-password")
async def reset_password(body: ResetPasswordIn):
    """
    Reset a user's password after verification.
    
    Updates the password for a user identified by userId (obtained from
    check_reset endpoint). The new password is hashed before storage.
    This endpoint should be called after verify_reset to ensure the user
    has been properly authenticated.
    
    Args:
        body: Request body containing:
            - userId: str (user UUID from check_reset)
            - newPassword: str (will be hashed before storage)
    
    Returns:
        dict: Response containing:
            - success: bool
            - data: dict with ok: True (if success)
            - error: dict with error code and message (if failure)
    
    Error codes:
        - USER_NOT_FOUND: User with provided userId not found
    """
    u = await User.get_or_none(id=body.userId)
    if not u:
        return {"success": False, "error": {"code": "USER_NOT_FOUND", "message": "User not found"}}
    u.password_hash = hash_password(body.newPassword)
    await u.save()
    return {"success": True, "data": {"ok": True}}

@router.post("/change-password")
async def change_password(body: ChangePasswordIn, user: User = Depends(get_current_user)):
    """
    Change password for the currently authenticated user.
    
    Updates the password for the logged-in user. The user is identified
    from the JWT token, so no userId is required. The new password is
    hashed before storage.
    
    Args:
        body: Request body containing:
            - newPassword: str (will be hashed before storage)
        user: Authenticated user (from dependency)
    
    Returns:
        dict: Response containing:
            - success: bool (always True on success)
            - data: dict with ok: True
    
    Raises:
        HTTPException (401): If user is not authenticated
    
    Note:
        This endpoint does not require the current password. For enhanced
        security, consider adding current password verification.
    """
    user.password_hash = hash_password(body.newPassword)
    await user.save()
    return {"success": True, "data": {"ok": True}}
