import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

CHAT_PAYLOAD = {
    "user_id": "user-test-001",
    "session_id": "session-test-001",
    "message": "Hello, what can you help me with?",
    "history": [],
    "metadata": {},
}


@pytest.mark.asyncio
async def test_chat_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_response_shape():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    data = response.json()
    assert "correlation_id" in data
    assert "answer" in data
    assert "selected_agent" in data
    assert "memory_used" in data
    assert "retrieval_used" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0


@pytest.mark.asyncio
async def test_chat_selects_support_agent_for_generic_message():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    data = response.json()
    assert data["selected_agent"] == "support"


@pytest.mark.asyncio
async def test_chat_selects_escalation_agent():
    payload = {**CHAT_PAYLOAD, "message": "This is urgent, please escalate"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json=payload)
    data = response.json()
    assert data["selected_agent"] == "escalation"
    assert data["event_summary"]["escalated"] is True


@pytest.mark.asyncio
async def test_chat_propagates_correlation_id():
    custom_id = "custom-correlation-xyz"
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Correlation-ID": custom_id},
    ) as client:
        response = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    assert response.headers.get("x-correlation-id") == custom_id
