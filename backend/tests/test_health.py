import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert data["service"] == "nexus-ai"


@pytest.mark.asyncio
async def test_health_has_correlation_id_header():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert "x-correlation-id" in response.headers


@pytest.mark.asyncio
async def test_ready_returns_structured_dependency_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ready", "degraded"}
    assert "dependencies" in data
    assert "database" in data["dependencies"]
    assert "qdrant" in data["dependencies"]
    assert "available" in data["dependencies"]["database"]
