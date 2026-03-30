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
    assert "conversation_id" in data
    assert "messages_count" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0


@pytest.mark.asyncio
async def test_chat_creates_conversation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    data = response.json()
    assert data["conversation_id"] is not None
    assert len(data["conversation_id"]) == 36  # UUID4 format
    assert data["messages_count"] == 2  # user message + assistant response


@pytest.mark.asyncio
async def test_chat_continues_existing_conversation():
    """A second request with the same conversation_id should grow messages_count."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
        conversation_id = first.json()["conversation_id"]

        second = await client.post(
            "/api/v1/chat",
            json={**CHAT_PAYLOAD, "message": "Follow-up question", "conversation_id": conversation_id},
        )
    data = second.json()
    assert data["conversation_id"] == conversation_id
    assert data["messages_count"] == 4  # 2 from first turn + 2 from second


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
