import uuid

import pytest


pytestmark = pytest.mark.asyncio


async def register_user(client, username: str, email: str, password: str):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    return resp


async def login_user(client, username: str, password: str):
    return await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )


async def test_register_and_login_flow(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    email = f"{username}@example.com"
    password = "StrongPass!23"

    resp = await register_user(client, username, email, password)
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert body["data"]["username"] == username

    # Duplicate username should fail
    dup_resp = await register_user(client, username, email, password)
    dup_body = dup_resp.json()
    assert dup_resp.status_code == 200
    assert dup_body["success"] is False
    assert dup_body["error"]["code"] == "USERNAME_EXISTS"

    # Successful login
    login_resp = await login_user(client, username, password)
    login_body = login_resp.json()
    assert login_resp.status_code == 200
    assert login_body["success"] is True
    assert "accessToken" in login_body["data"]
    assert "accessToken" in login_resp.cookies

    # Invalid password
    bad_login = await login_user(client, username, "wrong")
    assert bad_login.status_code == 401
    assert bad_login.json()["detail"]["code"] == "AUTH_INVALID_CREDENTIALS"


async def test_me_change_password_and_logout(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    password = "UserInit#123"
    new_password = "UserNew#456"
    await register_user(client, username, f"{username}@example.com", password)

    login_resp = await login_user(client, username, password)
    token = login_resp.json()["data"]["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    me_body = me_resp.json()
    assert me_resp.status_code == 200
    assert me_body["data"]["username"] == username

    change_resp = await client.post(
        "/api/v1/auth/change-password",
        json={"newPassword": new_password},
        headers=headers,
    )
    assert change_resp.status_code == 200
    assert change_resp.json()["data"]["ok"] is True

    # Old password should fail, new password succeeds
    old_login = await login_user(client, username, password)
    assert old_login.status_code == 401
    new_login = await login_user(client, username, new_password)
    assert new_login.status_code == 200

    logout_resp = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["success"] is True


async def test_reset_password_flow(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    email = f"{username}@example.com"
    password = "ResetMe#12"
    updated_password = "ResetDone#34"
    await register_user(client, username, email, password)

    # Wrong email should fail
    check_fail = await client.post(
        "/api/v1/auth/check-reset",
        json={"username": username, "email": "wrong@example.com"},
    )
    assert check_fail.status_code == 200
    assert check_fail.json()["success"] is False

    check_resp = await client.post(
        "/api/v1/auth/check-reset",
        json={"username": username, "email": email},
    )
    user_id = check_resp.json()["data"]["userId"]

    reset_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"userId": user_id, "newPassword": updated_password},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["data"]["ok"] is True

    login_resp = await login_user(client, username, updated_password)
    assert login_resp.status_code == 200


async def test_auth_requires_token(client):
    unauth_me = await client.get("/api/v1/auth/me")
    assert unauth_me.status_code == 401
    assert unauth_me.json()["detail"] == "AUTH_REQUIRED"

    unauth_change = await client.post(
        "/api/v1/auth/change-password", json={"newPassword": "Test1234"}
    )
    assert unauth_change.status_code == 401

