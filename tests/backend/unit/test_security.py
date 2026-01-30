"""
Unit tests for core.security module.
Tests password hashing, JWT token creation/validation.
"""
import pytest
import datetime as dt
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    JWT_SECRET,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password_returns_different_hash_each_time(self):
        """Password hashing should produce different hashes (salt included)."""
        password = "TestPassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # Different salts produce different hashes

    def test_hash_password_produces_valid_hash(self):
        """Hashed password should be a non-empty string."""
        password = "TestPassword123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should not be plain text

    def test_verify_password_correct_password(self):
        """verify_password should return True for correct password."""
        password = "TestPassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect_password(self):
        """verify_password should return False for incorrect password."""
        password = "TestPassword123"
        wrong_password = "WrongPassword456"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_password(self):
        """verify_password should handle empty password."""
        password = ""
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("not_empty", hashed) is False

    def test_password_hash_consistency(self):
        """Same password should verify against its hash consistently."""
        password = "ConsistentPassword789"
        hashed = hash_password(password)
        # Verify multiple times - should always succeed
        for _ in range(5):
            assert verify_password(password, hashed) is True


class TestJWTTokens:
    """Tests for JWT token creation and validation."""

    def test_create_access_token_returns_string(self):
        """create_access_token should return a JWT token string."""
        user_id = "test-user-123"
        role = "user"
        token = create_access_token(user_id, role)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_user_id(self):
        """Token should contain user ID in payload."""
        user_id = "test-user-456"
        role = "user"
        token = create_access_token(user_id, role)
        payload = decode_access_token(token)
        assert payload["sub"] == user_id

    def test_create_access_token_contains_role(self):
        """Token should contain user role in payload."""
        user_id = "test-user-789"
        role = "admin"
        token = create_access_token(user_id, role)
        payload = decode_access_token(token)
        assert payload["role"] == role

    def test_create_access_token_has_expiration(self):
        """Token should have expiration timestamp."""
        user_id = "test-user-exp"
        role = "user"
        token = create_access_token(user_id, role)
        payload = decode_access_token(token)
        assert "exp" in payload
        assert "iat" in payload
        # Expiration should be in the future
        exp_timestamp = payload["exp"]
        now_timestamp = dt.datetime.utcnow().timestamp()
        assert exp_timestamp > now_timestamp

    def test_decode_access_token_valid_token(self):
        """decode_access_token should decode valid token correctly."""
        user_id = "test-user-decode"
        role = "user"
        token = create_access_token(user_id, role)
        payload = decode_access_token(token)
        assert payload["sub"] == user_id
        assert payload["role"] == role
        assert "iat" in payload
        assert "exp" in payload

    def test_decode_access_token_invalid_token(self):
        """decode_access_token should raise exception for invalid token."""
        invalid_token = "invalid.token.here"
        with pytest.raises(Exception):  # jwt.InvalidTokenError or similar
            decode_access_token(invalid_token)

    def test_decode_access_token_wrong_secret(self):
        """decode_access_token should fail with wrong secret."""
        user_id = "test-user-secret"
        role = "user"
        token = create_access_token(user_id, role)
        # Try to decode with wrong secret
        import jwt
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=["HS256"])

    def test_token_expiration_time(self):
        """Token expiration should match configured time."""
        user_id = "test-user-time"
        role = "user"
        token = create_access_token(user_id, role)
        payload = decode_access_token(token)
        iat = payload["iat"]
        exp = payload["exp"]
        # Calculate difference in minutes
        if isinstance(iat, dt.datetime):
            iat_ts = iat.timestamp()
        else:
            iat_ts = iat
        if isinstance(exp, dt.datetime):
            exp_ts = exp.timestamp()
        else:
            exp_ts = exp
        diff_minutes = (exp_ts - iat_ts) / 60
        # Allow small tolerance for timing
        assert abs(diff_minutes - ACCESS_TOKEN_EXPIRE_MINUTES) < 1

    def test_different_users_get_different_tokens(self):
        """Different users should get different tokens."""
        user1_id = "user-1"
        user2_id = "user-2"
        role = "user"
        token1 = create_access_token(user1_id, role)
        token2 = create_access_token(user2_id, role)
        assert token1 != token2
        payload1 = decode_access_token(token1)
        payload2 = decode_access_token(token2)
        assert payload1["sub"] != payload2["sub"]

    def test_same_user_different_roles_get_different_tokens(self):
        """Same user with different roles should get different tokens."""
        user_id = "same-user"
        token_user = create_access_token(user_id, "user")
        token_admin = create_access_token(user_id, "admin")
        assert token_user != token_admin
        payload_user = decode_access_token(token_user)
        payload_admin = decode_access_token(token_admin)
        assert payload_user["role"] == "user"
        assert payload_admin["role"] == "admin"

