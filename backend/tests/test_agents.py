"""
Tests for Phase 3 Step 1 — multi-agent orchestration and agent selection.

All tests run against SQLite in-memory (via conftest.override_db) and do not
require live OpenAI, Qdrant, or Postgres services.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.agents import AGENT_REGISTRY
from app.services.agents.base import AgentResult

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

BASE_PAYLOAD = {
    "user_id": "user-agent-test",
    "session_id": "session-agent-test",
    "history": [],
    "metadata": {},
}


def _payload(message: str) -> dict:
    return {**BASE_PAYLOAD, "message": message}


def _make_ctx(message: str, retrieval_context: str = "", memory: dict | None = None) -> dict:
    """Minimal orchestrator context for unit-testing agents directly."""
    from unittest.mock import MagicMock
    request = MagicMock()
    request.user_id = "u1"
    request.session_id = "s1"
    request.message = message
    request.history = []
    request.metadata = {}
    return {
        "request": request,
        "correlation_id": "test-corr",
        "retrieval_context": retrieval_context,
        "retrieval_results": [],
        "retrieval_used": bool(retrieval_context),
        "memory": memory or {},
        "memory_used": bool(memory),
        "confidence": 0.0,
        "escalated": False,
        "agent_result": None,
        "events": [],
    }


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------

def test_agent_registry_has_all_five_agents():
    assert set(AGENT_REGISTRY.keys()) == {"support", "research", "summarizer", "planner", "escalation"}


def test_agent_registry_names_match_keys():
    for name, agent in AGENT_REGISTRY.items():
        assert agent.name == name


# ---------------------------------------------------------------------------
# Triage / agent selection via HTTP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_triage_selects_support_for_generic_message():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("Hello, what can you help me with?"))
    assert r.json()["selected_agent"] == "support"


@pytest.mark.asyncio
async def test_triage_selects_support_for_troubleshooting():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("My login is broken and I need help"))
    assert r.json()["selected_agent"] == "support"


@pytest.mark.asyncio
async def test_triage_selects_research_for_explain():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("Can you explain how RAG works?"))
    assert r.json()["selected_agent"] == "research"


@pytest.mark.asyncio
async def test_triage_selects_research_for_what_is():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("What is Nexus AI?"))
    assert r.json()["selected_agent"] == "research"


@pytest.mark.asyncio
async def test_triage_selects_research_for_compare():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("Compare GPT-4 and Claude"))
    assert r.json()["selected_agent"] == "research"


@pytest.mark.asyncio
async def test_triage_selects_summarizer_for_summarize():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("Please summarize our conversation so far"))
    assert r.json()["selected_agent"] == "summarizer"


@pytest.mark.asyncio
async def test_triage_selects_summarizer_for_tldr():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("Give me a tldr of this document"))
    assert r.json()["selected_agent"] == "summarizer"


@pytest.mark.asyncio
async def test_triage_selects_planner_for_plan():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("Create a plan to build a REST API"))
    assert r.json()["selected_agent"] == "planner"


@pytest.mark.asyncio
async def test_triage_selects_planner_for_roadmap():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("What is the roadmap for this feature?"))
    assert r.json()["selected_agent"] == "planner"


@pytest.mark.asyncio
async def test_triage_selects_escalation_for_urgent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("This is urgent, I need a refund now"))
    assert r.json()["selected_agent"] == "escalation"


@pytest.mark.asyncio
async def test_triage_selects_escalation_for_angry():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("I am angry and want to speak to a manager"))
    assert r.json()["selected_agent"] == "escalation"


@pytest.mark.asyncio
async def test_triage_selects_escalation_for_legal():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("I have a legal concern about data privacy"))
    assert r.json()["selected_agent"] == "escalation"


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_response_includes_confidence():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("Hello"))
    data = r.json()
    assert "confidence" in data
    assert isinstance(data["confidence"], float)
    assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_chat_response_includes_selected_agent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("Tell me a plan for my startup"))
    data = r.json()
    assert data["selected_agent"] == "planner"
    assert len(data["answer"]) > 0


@pytest.mark.asyncio
async def test_escalation_sets_escalated_in_event_summary():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("I want to escalate this complaint"))
    data = r.json()
    assert data["selected_agent"] == "escalation"
    assert data["event_summary"]["escalated"] is True


# ---------------------------------------------------------------------------
# Agent unit tests — direct run() calls
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_support_agent_returns_agent_result():
    ctx = _make_ctx("My account is not working")
    ctx = await AGENT_REGISTRY["support"].run(ctx)
    result: AgentResult = ctx["agent_result"]
    assert isinstance(result, AgentResult)
    assert result.agent_name == "support"
    assert len(result.answer) > 0
    assert 0.0 <= result.confidence <= 1.0
    assert result.escalation_required is False


@pytest.mark.asyncio
async def test_support_agent_uses_retrieval_context():
    ctx = _make_ctx("help with login", retrieval_context="Login docs: use SSO.")
    ctx = await AGENT_REGISTRY["support"].run(ctx)
    result: AgentResult = ctx["agent_result"]
    assert result.confidence >= 0.85
    assert "knowledge base" in ctx["answer"].lower()


@pytest.mark.asyncio
async def test_research_agent_returns_agent_result():
    ctx = _make_ctx("Explain vector databases")
    ctx = await AGENT_REGISTRY["research"].run(ctx)
    result: AgentResult = ctx["agent_result"]
    assert isinstance(result, AgentResult)
    assert result.agent_name == "research"
    assert len(result.answer) > 0


@pytest.mark.asyncio
async def test_research_agent_uses_retrieval_context():
    ctx = _make_ctx("What is Qdrant?", retrieval_context="Qdrant is a vector search engine.")
    ctx = await AGENT_REGISTRY["research"].run(ctx)
    result: AgentResult = ctx["agent_result"]
    assert result.confidence >= 0.8
    assert "source" in ctx["answer"].lower() or "finding" in ctx["answer"].lower()


@pytest.mark.asyncio
async def test_summarizer_agent_with_no_context_returns_guidance():
    ctx = _make_ctx("Summarize the conversation")
    ctx = await AGENT_REGISTRY["summarizer"].run(ctx)
    result: AgentResult = ctx["agent_result"]
    assert isinstance(result, AgentResult)
    assert len(ctx["answer"]) > 0
    assert result.confidence < 0.5  # low confidence when no content available


@pytest.mark.asyncio
async def test_summarizer_agent_with_recent_messages():
    memory = {
        "recent_messages": [
            {"role": "user", "content": "What is Nexus AI?"},
            {"role": "assistant", "content": "It is a multi-agent platform."},
        ],
        "summary_text": None,
        "memory_used": True,
        "memory_source": "db",
    }
    ctx = _make_ctx("Summarize", memory=memory)
    ctx["memory_used"] = True
    ctx = await AGENT_REGISTRY["summarizer"].run(ctx)
    result: AgentResult = ctx["agent_result"]
    assert result.confidence >= 0.85
    assert "USER" in ctx["answer"] or "ASSISTANT" in ctx["answer"]


@pytest.mark.asyncio
async def test_planner_agent_returns_numbered_steps():
    ctx = _make_ctx("How to build a SaaS product")
    ctx = await AGENT_REGISTRY["planner"].run(ctx)
    result: AgentResult = ctx["agent_result"]
    assert isinstance(result, AgentResult)
    assert "Step 1" in ctx["answer"]
    assert result.agent_name == "planner"


@pytest.mark.asyncio
async def test_escalation_agent_sets_escalation_required():
    ctx = _make_ctx("I want to sue your company, this is a legal matter")
    ctx = await AGENT_REGISTRY["escalation"].run(ctx)
    result: AgentResult = ctx["agent_result"]
    assert result.escalation_required is True
    assert ctx["escalated"] is True
    assert result.confidence == 1.0
    assert "escalated" in ctx["answer"].lower()


@pytest.mark.asyncio
async def test_escalation_agent_detects_reason():
    ctx = _make_ctx("I need a refund immediately")
    ctx = await AGENT_REGISTRY["escalation"].run(ctx)
    result: AgentResult = ctx["agent_result"]
    assert result.notes.get("detected_reason") == "billing/refund request"
