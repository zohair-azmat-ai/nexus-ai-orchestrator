import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db import crud
from app.db.postgres import get_db
from app.main import app


async def _create_user(email: str, role: str, password: str = "Password123!") -> None:
    async for db in get_db():
        await crud.create_user(
            db,
            email=email,
            full_name=email.split("@", 1)[0].title(),
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        await db.commit()
        break


async def _login(client: AsyncClient, email: str, password: str = "Password123!") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_login_success_and_me_endpoint():
    await _create_user("reviewer@example.com", "reviewer")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "reviewer@example.com", "password": "Password123!"},
        )

        assert login_response.status_code == 200
        body = login_response.json()
        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )

    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "reviewer"
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "reviewer@example.com"


@pytest.mark.asyncio
async def test_login_rejects_invalid_password():
    await _create_user("reviewer@example.com", "reviewer")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "reviewer@example.com", "password": "WrongPassword123!"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


@pytest.mark.asyncio
async def test_protected_escalation_endpoints_require_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        queue_response = await client.get("/api/v1/escalations")
        me_response = await client.get("/api/v1/auth/me")

    assert queue_response.status_code == 401
    assert me_response.status_code == 401


@pytest.mark.asyncio
async def test_user_role_cannot_access_reviewer_queue():
    await _create_user("user@example.com", "user")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client, "user@example.com")
        response = await client.get(
            "/api/v1/escalations",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions."


@pytest.mark.asyncio
async def test_reviewer_can_access_reviewer_queue():
    await _create_user("reviewer@example.com", "reviewer")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client, "reviewer@example.com")
        response = await client.get(
            "/api/v1/escalations",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert "cases" in response.json()
