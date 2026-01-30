import pytest


pytestmark = pytest.mark.asyncio


async def _login_headers(client, username: str, password: str):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


async def test_admin_user_management_flow(client, create_admin):
    admin, admin_password = await create_admin()
    admin_headers = await _login_headers(client, admin.username, admin_password)

    # Create a normal user via public endpoint
    user_payload = {"username": "member1", "email": "member1@example.com", "password": "Member#123"}
    register_resp = await client.post("/api/v1/auth/register", json=user_payload)
    user_id = register_resp.json()["data"]["id"]

    list_resp = await client.get("/api/v1/admin/users", headers=admin_headers, params={"offset": 0, "limit": 20})
    assert list_resp.status_code == 200
    assert any(item["username"] == "member1" for item in list_resp.json()["items"])

    detail_resp = await client.get(f"/api/v1/admin/users/{user_id}", headers=admin_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["user"]["username"] == "member1"

    update_resp = await client.patch(
        f"/api/v1/admin/users/{user_id}",
        headers=admin_headers,
        json={"email": "member1+updated@example.com", "role": "admin"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["user"]["email"] == "member1+updated@example.com"
    assert update_resp.json()["user"]["role"] == "admin"

    reset_resp = await client.post(
        f"/api/v1/admin/users/{user_id}/reset-password",
        headers=admin_headers,
        json={"newPassword": "Member#999"},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["data"]["ok"] is True

    login_with_new_pwd = await client.post(
        "/api/v1/auth/login",
        json={"username": "member1", "password": "Member#999"},
    )
    assert login_with_new_pwd.status_code == 200


async def test_admin_license_key_management(client, create_admin):
    admin, admin_password = await create_admin()
    admin_headers = await _login_headers(client, admin.username, admin_password)

    batch_resp = await client.post(
        "/api/v1/admin/license-keys/batch",
        headers=admin_headers,
        json={"count": 2, "keyType": "paid", "expireDays": 10, "prefix": "FAT"},
    )
    assert batch_resp.status_code == 200
    keys = batch_resp.json()["keys"]
    assert len(keys) == 2

    list_resp = await client.get("/api/v1/admin/license-keys", headers=admin_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 2

    detail_resp = await client.get(
        f"/api/v1/admin/license-keys/{keys[0]['id']}",
        headers=admin_headers,
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["data"]["id"] == keys[0]["id"]

    delete_resp = await client.delete(
        f"/api/v1/admin/license-keys/{keys[0]['id']}",
        headers=admin_headers,
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["data"]["ok"] is True

    # Verify key flow (accessible without admin)
    verify_resp = await client.post(
        "/api/v1/admin/verify-key",
        json={"key": keys[1]["key"], "consume": True},
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["success"] is True
    assert verify_resp.json()["data"]["ok"] is True

    # Second attempt should fail because key is consumed
    verify_again = await client.post(
        "/api/v1/admin/verify-key",
        json={"key": keys[1]["key"], "consume": True},
    )
    assert verify_again.status_code == 200
    assert verify_again.json()["data"]["ok"] is False


async def test_non_admin_cannot_access_admin_routes(client, create_user):
    user, password = await create_user()
    headers = await _login_headers(client, user.username, password)

    resp = await client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "FORBIDDEN_ADMIN_ONLY"

