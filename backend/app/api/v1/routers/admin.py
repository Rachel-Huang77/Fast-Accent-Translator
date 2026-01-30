# app/api/v1/routers/admin.py
from __future__ import annotations

import datetime as dt
import secrets
import string
from typing import Optional, List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel
from tortoise.expressions import Q

from app.api.v1.deps import require_admin, get_current_user
from app.models.user import User
from app.models.license_key import LicenseKey
from app.schemas.admin import (
    AdminUserListOut,
    AdminUserDetailOut,
    AdminUserUpdateIn,
    AdminResetPasswordIn,
)
from app.schemas.license_key import (
    BatchGenerateIn,
    BatchGenerateOut,
    GeneratedKeyItem,
    VerifyKeyIn,
)
from app.core.security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


# ------------------------------------------------------------------------------
# Helper: optional current user (for /admin/verify-key when consume=True to record redeemer)
# ------------------------------------------------------------------------------
async def optional_current_user_dependency():
    """
    Try to get current logged-in user; if failed return None (instead of throwing 401).
    Used for /admin/verify-key when consume=True to record used_by.
    """
    try:
        user = await get_current_user()  # Will try to get token from Authorization/Cookie
        return user
    except Exception:
        return None


def utc_now() -> dt.datetime:
    """
    Get current UTC datetime with timezone information.
    
    Returns:
        dt.datetime: Current UTC datetime with timezone awareness
    """
    return dt.datetime.now(dt.timezone.utc)


# ==============================================================================
# I. User Management Interface
#     Prefix: /api/v1/admin/users
# ==============================================================================
def _user_to_dict(u: User) -> dict:
    """
    Convert User model instance to dictionary format for API responses.
    
    Args:
        u: User model instance
    
    Returns:
        dict: Dictionary containing user fields formatted for API response
    """
    return {
        "id": str(u.id),
        "username": u.username,
        "email": u.email,
        "role": u.role,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


async def _count_admins() -> int:
    """
    Count the total number of admin users in the system.
    
    Returns:
        int: Number of users with role="admin"
    
    Note:
        Used to prevent demoting or deleting the last admin user.
    """
    return await User.filter(role="admin").count()


@router.get(
    "/users",
    response_model=AdminUserListOut,
    dependencies=[Depends(require_admin)],
)
async def list_users(
    q: str | None = Query(default=None, description="Fuzzy search by username/email"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get paginated list of all users (admin only).
    
    Returns a list of all users in the system with optional search filtering.
    Results are ordered by creation date (newest first).
    
    Args:
        q: Optional search query for fuzzy matching username or email
        offset: Number of items to skip (for pagination)
        limit: Maximum number of items to return (1-100)
    
    Returns:
        AdminUserListOut: Response containing paginated user list
    
    Raises:
        HTTPException (403): If user is not an admin
        HTTPException (401): If user is not authenticated
    """
    qs = User.all().order_by("-created_at")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))

    total = await qs.count()
    rows = await qs.offset(offset).limit(limit)
    items = [_user_to_dict(u) for u in rows]

    return {"items": items, "offset": offset, "limit": limit, "total": total}


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetailOut,
    dependencies=[Depends(require_admin)],
)
async def get_user_detail(user_id: str):
    """
    Get detailed information about a specific user (admin only).
    
    Args:
        user_id: User UUID string
    
    Returns:
        AdminUserDetailOut: Response containing user details
    
    Raises:
        HTTPException (404): If user not found
        HTTPException (403): If user is not an admin
        HTTPException (401): If user is not authenticated
    """
    u = await User.get_or_none(id=user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND")
    return {"user": _user_to_dict(u)}


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserDetailOut,
    dependencies=[Depends(require_admin)],
)
async def update_user(
    user_id: str,
    body: AdminUserUpdateIn,
    current_admin: User = Depends(get_current_user),
):
    """
    Update user information (admin only).
    
    Allows admins to update a user's username, email, or role. All fields
    are optional - only provided fields will be updated. Includes validation
    to prevent security issues (e.g., demoting last admin, demoting self).
    
    Args:
        user_id: User UUID string to update
        body: Request body with optional fields to update
        current_admin: Current admin user (from dependency)
    
    Returns:
        AdminUserDetailOut: Response containing updated user details
    
    Raises:
        HTTPException (404): If user not found
        HTTPException (400): If validation fails (username/email exists, cannot demote self, etc.)
        HTTPException (403): If user is not an admin
        HTTPException (401): If user is not authenticated
    """
    u = await User.get_or_none(id=user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND")

    # 1) Update username (uniqueness check)
    if body.username and body.username != u.username:
        exists = await User.filter(username=body.username).exclude(id=user_id).exists()
        if exists:
            raise HTTPException(
                status_code=400,
                detail={"code": "USERNAME_EXISTS", "message": "Username already exists"},
            )
        u.username = body.username

    # 2) Update email (uniqueness check, allow null)
    if body.email is not None and body.email != u.email:
        if body.email != "":
            email_taken = await User.filter(email=body.email).exclude(id=user_id).exists()
            if email_taken:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "EMAIL_EXISTS", "message": "Email already registered"},
                )
            u.email = body.email
        else:
            u.email = None

    # 3) Update role (cannot demote self; cannot demote last admin to user)
    if body.role and body.role != u.role:
        if str(current_admin.id) == str(u.id) and body.role != "admin":
            raise HTTPException(
                status_code=400,
                detail={"code": "CANNOT_DEMOTE_SELF", "message": "Cannot demote yourself"},
            )

        if u.role == "admin" and body.role == "user":
            admin_count = await _count_admins()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "LAST_ADMIN_FORBIDDEN", "message": "Cannot demote the last admin"},
                )
        u.role = body.role

    await u.save()
    return {"user": _user_to_dict(u)}


@router.delete(
    "/users/{user_id}",
    dependencies=[Depends(require_admin)],
)
async def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_user),
):
    """
    Delete a user account (admin only).
    
    Permanently deletes a user account. Includes validation to prevent
    security issues (e.g., deleting self, deleting last admin).
    
    Args:
        user_id: User UUID string to delete
        current_admin: Current admin user (from dependency)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with ok: True
    
    Raises:
        HTTPException (404): If user not found
        HTTPException (400): If validation fails (cannot delete self, cannot delete last admin)
        HTTPException (403): If user is not an admin
        HTTPException (401): If user is not authenticated
    """
    u = await User.get_or_none(id=user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND")

    # Cannot delete self
    if str(current_admin.id) == str(u.id):
        raise HTTPException(
            status_code=400,
            detail={"code": "CANNOT_DELETE_SELF", "message": "Cannot delete yourself"},
        )

    # Cannot delete last admin
    if u.role == "admin":
        admin_count = await _count_admins()
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail={"code": "LAST_ADMIN_FORBIDDEN", "message": "Cannot delete the last admin"},
            )

    await u.delete()
    return {"success": True, "data": {"ok": True}}


@router.post(
    "/users/{user_id}/reset-password",
    dependencies=[Depends(require_admin)],
)
async def reset_user_password(
    user_id: str,
    body: AdminResetPasswordIn,
    current_admin: User = Depends(get_current_user),
):
    """
    Reset a user's password (admin only).
    
    Allows admins to reset any user's password without knowing the current
    password. The new password is hashed before storage.
    
    Args:
        user_id: User UUID string whose password to reset
        body: Request body containing newPassword
        current_admin: Current admin user (from dependency)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with ok: True
    
    Raises:
        HTTPException (404): If user not found
        HTTPException (403): If user is not an admin
        HTTPException (401): If user is not authenticated
    """
    u = await User.get_or_none(id=user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND")

    u.password_hash = hash_password(body.newPassword)
    await u.save()
    return {"success": True, "data": {"ok": True}}


# ==============================================================================
# II. Key Management (batch generation, list, detail, delete)
#     Prefix: /api/v1/admin/license-keys/*
#     Note: Don't return plaintext, only return plaintext collection once during generation
# ==============================================================================
def _make_plain_key(prefix: str = "FAT") -> str:
    """
    Generate plaintext key in format like FAT-AB12-CD34-EF56-GH78.
    Only returned to frontend once; database only stores sha256(key).
    """
    alphabet = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(alphabet) for _ in range(4)) for __ in range(4)]
    return f"{prefix}-{parts[0]}-{parts[1]}-{parts[2]}-{parts[3]}"


@router.post(
    "/license-keys/batch",
    response_model=BatchGenerateOut,
    dependencies=[Depends(require_admin)],
)
async def batch_generate_keys(body: BatchGenerateIn):
    """
    Batch generate license keys (admin only).
    
    Generates multiple license keys at once with the specified type, prefix,
    and optional expiration. Keys are stored as SHA256 hashes in the database
    for security. Plaintext keys are only returned once during generation.
    
    Args:
        body: Request body containing:
            - count: int (number of keys to generate, 1-200)
            - keyType: str (key type, e.g., "paid", "trial")
            - expireDays: int | None (days until expiration, None for no expiration)
            - prefix: str | None (key prefix, default "FAT")
    
    Returns:
        BatchGenerateOut: Response containing list of generated keys with plaintext
    
    Raises:
        HTTPException (500): If key generation collision occurs (extremely rare)
        HTTPException (403): If user is not an admin
        HTTPException (401): If user is not authenticated
    
    Note:
        - Plaintext keys are only returned in this response, never stored in database
        - Database stores SHA256 hash, prefix, and last 4 characters for display
        - Each key is checked for uniqueness before creation
    """
    count = body.count
    key_type = body.keyType.strip()
    prefix = (body.prefix or "FAT").strip().upper()
    expires_at: Optional[dt.datetime] = None

    if body.expireDays:
        expires_at = utc_now() + dt.timedelta(days=body.expireDays)

    items: List[GeneratedKeyItem] = []

    for _ in range(count):
    # Ensure hash is unique
        for __ in range(10):  # Try at most 10 times to avoid extreme duplicates
            plain = _make_plain_key(prefix)
            h = LicenseKey.sha256_hex(plain)
            exists = await LicenseKey.filter(key_hash=h).exists()
            if not exists:
                # ⭐ Parse prefix and last 4 characters from plaintext
                # plain format like FAT-AB12-CD34-EF56-GH78
                parts = plain.split("-")
                key_prefix = parts[0]
                key_suffix_last4 = parts[-1]

                lk = await LicenseKey.create(
                    key_hash=h,
                    key_type=key_type,
                    expires_at=expires_at,
                    is_used=False,
                    prefix=key_prefix,
                    suffix_last4=key_suffix_last4,
                )
                items.append(
                    GeneratedKeyItem(
                        id=str(lk.id),
                        key=plain,  # Only return plaintext in generation interface
                        keyType=key_type,
                        expiresAt=lk.expires_at.isoformat() if lk.expires_at else None,
                    )
                )
                break
        else:
            raise HTTPException(status_code=500, detail="KEY_GENERATION_COLLISION")



    return {"keys": items}


class LicenseKeyListOut(BaseModel):
    items: list[dict]
    offset: int
    limit: int
    total: int


@router.get(
    "/license-keys",
    response_model=LicenseKeyListOut,
    dependencies=[Depends(require_admin)],
)
async def list_license_keys(
    is_used: Optional[bool] = Query(default=None),
    key_type: Optional[str] = Query(default=None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    """
    Get paginated list of license keys (admin only).
    
    Returns a list of all license keys with optional filtering by usage status
    and key type. Results are ordered by creation date (newest first).
    
    Args:
        is_used: Optional filter for used/unused keys (True/False/None for all)
        key_type: Optional filter for key type (e.g., "paid", "trial")
        offset: Number of items to skip (for pagination)
        limit: Maximum number of items to return (1-200)
    
    Returns:
        LicenseKeyListOut: Response containing paginated key list with metadata
    
    Raises:
        HTTPException (403): If user is not an admin
        HTTPException (401): If user is not authenticated
    
    Note:
        Keys are displayed with masked format: "PREFIX-****-****-LAST4"
        Plaintext keys are never returned in list responses.
    """
    qs = LicenseKey.all().order_by("-created_at")
    if is_used is not None:
        qs = qs.filter(is_used=is_used)
    if key_type:
        qs = qs.filter(key_type=key_type)

    total = await qs.count()
    rows = await qs.offset(offset).limit(limit)

    now = utc_now()
    items = []
    for r in rows:
        expired = bool(r.expires_at and r.expires_at <= now)

        if r.prefix and r.suffix_last4:
            
            key_preview = f"{r.prefix}-****-****-{r.suffix_last4}"
        else:
            key_preview = None  # Compatible with old data

        items.append(
            {
                "id": str(r.id),
                "keyType": r.key_type,
                "isUsed": r.is_used,
                "usedBy": str(r.used_by_id) if r.used_by_id else None,
                "usedAt": r.used_at.isoformat() if r.used_at else None,
                "expiresAt": r.expires_at.isoformat() if r.expires_at else None,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
                "isExpired": expired,
                # ⭐ New field: prefix + **** + last 4 characters
                "keyPreview": key_preview,
            }
        )

    return {"items": items, "offset": offset, "limit": limit, "total": total}




@router.get(
    "/license-keys/{key_id}",
    dependencies=[Depends(require_admin)],
)
async def get_license_key_detail(key_id: str):
    """
    Get detailed information about a specific license key (admin only).
    
    Args:
        key_id: License key UUID string
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with key details (id, keyType, isUsed, usedBy, usedAt, expiresAt, createdAt, isExpired)
    
    Raises:
        HTTPException (404): If key not found
        HTTPException (403): If user is not an admin
        HTTPException (401): If user is not authenticated
    """
    r = await LicenseKey.get_or_none(id=key_id)
    if not r:
        raise HTTPException(status_code=404, detail="KEY_NOT_FOUND")
    now = utc_now()
    return {
        "success": True,
        "data": {
            "id": str(r.id),
            "keyType": r.key_type,
            "isUsed": r.is_used,
            "usedBy": str(r.used_by_id) if r.used_by_id else None,
            "usedAt": r.used_at.isoformat() if r.used_at else None,
            "expiresAt": r.expires_at.isoformat() if r.expires_at else None,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
            "isExpired": bool(r.expires_at and r.expires_at <= now),
        },
    }


@router.delete(
    "/license-keys/{key_id}",
    dependencies=[Depends(require_admin)],
)
async def delete_license_key(key_id: str):
    """
    Delete a license key (admin only).
    
    Permanently deletes a license key from the database. This action cannot
    be undone. Used keys can also be deleted.
    
    Args:
        key_id: License key UUID string to delete
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with ok: True
    
    Raises:
        HTTPException (404): If key not found
        HTTPException (403): If user is not an admin
        HTTPException (401): If user is not authenticated
    """
    r = await LicenseKey.get_or_none(id=key_id)
    if not r:
        raise HTTPException(status_code=404, detail="KEY_NOT_FOUND")
    await r.delete()
    return {"success": True, "data": {"ok": True}}


# ==============================================================================
# III. Key Verification (compatible with frontend: /api/v1/admin/verify-key)
#     Notes:
#       - For compatibility, admin not required here; regular users can also call verify/redeem
#       - When body.consume=True, if already logged in, will record used_by; otherwise only mark as used
# ==============================================================================
@router.post("/verify-key")
async def verify_key(
    body: VerifyKeyIn,
    current_user: Optional[User] = Depends(optional_current_user_dependency),
):
    """
    Verify and optionally consume a license key.
    
    Validates a license key and optionally marks it as used. This endpoint
    is accessible to both authenticated and unauthenticated users (for
    compatibility with frontend key verification flow).
    
    If consume=True and a user is logged in, the key's used_by field is
    recorded. If no user is logged in, the key is still marked as used but
    without a user association.
    
    Args:
        body: Request body containing:
            - key: str (plaintext license key to verify)
            - consume: bool (if True, mark key as used after verification)
        current_user: Optional authenticated user (from dependency, can be None)
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with ok: bool (True if key is valid and available, False otherwise)
    
    Note:
        - Returns ok=False for invalid, expired, or already-used keys
        - Does not expose detailed error information to prevent key enumeration
        - If consume=True, the key cannot be used again
    """
    plain = (body.key or "").strip().upper()
    if not plain:
        return {"success": False, "error": {"code": "BAD_REQUEST", "message": "key required"}}

    h = LicenseKey.sha256_hex(plain)
    r = await LicenseKey.get_or_none(key_hash=h)
    if not r:
        return {"success": True, "data": {"ok": False}}  # Don't expose more information

    # Expiration check
    if r.expires_at and r.expires_at <= utc_now():
        return {"success": True, "data": {"ok": False}}

    # Already used check
    if r.is_used:
        return {"success": True, "data": {"ok": False}}

    # Only verify: return ok=True
    if not body.consume:
        return {"success": True, "data": {"ok": True}}

    # consume=True: Mark as used; if have logged-in user then record used_by
    r.is_used = True
    r.used_at = utc_now()
    if current_user:
        r.used_by = current_user
    await r.save()
    return {"success": True, "data": {"ok": True}}
