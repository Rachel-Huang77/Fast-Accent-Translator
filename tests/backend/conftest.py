import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.core import db as db_module
from app.core.security import hash_password
from app.main import app
from app.models.user import User


TEST_DB_URL = "sqlite://:memory:?cache=shared"
os.environ["DATABASE_URL"] = TEST_DB_URL
db_module.DB_URL = TEST_DB_URL
db_module.TORTOISE_ORM["connections"]["default"] = TEST_DB_URL


async def _init_test_db() -> None:
    """
    Initialize a clean in-memory SQLite database for every test.
    Ensures tables are recreated from scratch.
    """
    if Tortoise._inited:
        await Tortoise.close_connections()
    await Tortoise.init(config=db_module.TORTOISE_ORM)
    await Tortoise.generate_schemas()


@pytest_asyncio.fixture
async def client():
    """
    Provide an HTTPX AsyncClient bound to the FastAPI app with a fresh DB.
    """
    await _init_test_db()
    # Use ASGITransport without lifespan parameter (not supported in all httpx versions)
    try:
        transport = ASGITransport(app=app, lifespan="off")
    except TypeError:
        # Fallback for httpx versions that don't support lifespan parameter
        transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
    await Tortoise.close_connections()


@pytest_asyncio.fixture
async def create_admin():
    """
    Factory fixture to create admin users directly via ORM for privileged endpoints.
    """

    async def _create_admin(password: str = "AdminPass!23") -> tuple[User, str]:
        user = await User.create(
            username=f"admin_{uuid.uuid4().hex[:6]}",
            email="admin@example.com",
            password_hash=hash_password(password),
            role="admin",
        )
        return user, password

    return _create_admin


@pytest_asyncio.fixture
async def create_user():
    """
    Factory fixture to create regular users directly.
    """

    async def _create_user(password: str = "UserPass!23") -> tuple[User, str]:
        user = await User.create(
            username=f"user_{uuid.uuid4().hex[:6]}",
            email=f"{uuid.uuid4().hex[:6]}@example.com",
            password_hash=hash_password(password),
            role="user",
        )
        return user, password

    return _create_user


@pytest_asyncio.fixture
async def auth_header_factory(client):
    """
    Helper fixture to obtain Authorization headers via the login endpoint.
    """

    async def _get_headers(username: str, password: str) -> dict[str, str]:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["data"]["accessToken"]
        return {"Authorization": f"Bearer {token}"}

    return _get_headers

