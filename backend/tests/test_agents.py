"""
Tests for Phase 3 Steps 1 & 2 — multi-agent orchestration and LLM-powered intelligence.

All tests run against SQLite in-memory (via conftest.override_db) and do not
require live OpenAI, Qdrant, or Postgres services.
LLM path tests mock openai_client.complete() so no real API key is needed.
"""

import pytest
from unittest.mock import AsyncMock, patch
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
    # Force deterministic path to test template-based answer
    with patch("app.core.config.settings.openai_api_key", ""):
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
    # Force deterministic path to test template-based answer
    with patch("app.core.config.settings.openai_api_key", ""):
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
    # Force deterministic path to test template-based bullet format
    with patch("app.core.config.settings.openai_api_key", ""):
        ctx = await AGENT_REGISTRY["summarizer"].run(ctx)
    result: AgentResult = ctx["agent_result"]
    assert result.confidence >= 0.85
    assert "USER" in ctx["answer"] or "ASSISTANT" in ctx["answer"]


@pytest.mark.asyncio
async def test_planner_agent_returns_numbered_steps():
    ctx = _make_ctx("How to build a SaaS product")
    # Force deterministic path to test template-based steps
    with patch("app.core.config.settings.openai_api_key", ""):
        ctx = await AGENT_REGISTRY["planner"].run(ctx)
    result: AgentResult = ctx["agent_result"]
    assert isinstance(result, AgentResult)
    assert "Step 1" in ctx["answer"]
    assert result.agent_name == "planner"


@pytest.mark.asyncio
async def test_escalation_agent_sets_escalation_required():
    ctx = _make_ctx("I want to sue your company, this is a legal matter")
    # Force deterministic path so we can assert on template phrasing
    with patch("app.core.config.settings.openai_api_key", ""):
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


# ---------------------------------------------------------------------------
# Phase 3 Step 2 — LLM path tests (openai_client.complete is mocked)
# ---------------------------------------------------------------------------

_LLM_PATCH = "app.services.llm.openai_client.openai_client.complete"
_SETTINGS_PATCH = "app.core.config.settings.openai_api_key"


@pytest.mark.asyncio
async def test_support_agent_calls_llm_when_key_is_set():
    ctx = _make_ctx("My feature is broken")
    with (
        patch(_SETTINGS_PATCH, "sk-fake-key"),
        patch(_LLM_PATCH, new_callable=AsyncMock, return_value="LLM support answer") as mock_llm,
    ):
        ctx = await AGENT_REGISTRY["support"].run(ctx)

    mock_llm.assert_called_once()
    assert ctx["answer"] == "LLM support answer"
    assert ctx["agent_result"].confidence >= 0.75


@pytest.mark.asyncio
async def test_support_agent_falls_back_without_api_key():
    ctx = _make_ctx("My feature is broken")
    with patch(_SETTINGS_PATCH, ""):
        ctx = await AGENT_REGISTRY["support"].run(ctx)

    # No LLM used — deterministic fallback
    assert len(ctx["answer"]) > 0
    assert ctx["agent_result"].confidence == 0.5  # no context, no llm


@pytest.mark.asyncio
async def test_support_agent_falls_back_on_llm_error():
    ctx = _make_ctx("Something is wrong")
    with (
        patch(_SETTINGS_PATCH, "sk-fake-key"),
        patch(_LLM_PATCH, new_callable=AsyncMock, side_effect=RuntimeError("API error")),
    ):
        ctx = await AGENT_REGISTRY["support"].run(ctx)

    # Should produce a deterministic answer, not raise
    assert len(ctx["answer"]) > 0
    assert ctx["agent_result"].confidence == 0.5


@pytest.mark.asyncio
async def test_research_agent_calls_llm_when_key_is_set():
    ctx = _make_ctx("Explain how vector search works")
    with (
        patch(_SETTINGS_PATCH, "sk-fake-key"),
        patch(_LLM_PATCH, new_callable=AsyncMock, return_value="LLM research answer") as mock_llm,
    ):
        ctx = await AGENT_REGISTRY["research"].run(ctx)

    mock_llm.assert_called_once()
    assert ctx["answer"] == "LLM research answer"


@pytest.mark.asyncio
async def test_summarizer_agent_calls_llm_when_content_and_key_present():
    memory = {
        "recent_messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}],
        "summary_text": None,
    }
    ctx = _make_ctx("Summarize", memory=memory)
    with (
        patch(_SETTINGS_PATCH, "sk-fake-key"),
        patch(_LLM_PATCH, new_callable=AsyncMock, return_value="LLM summary") as mock_llm,
    ):
        ctx = await AGENT_REGISTRY["summarizer"].run(ctx)

    mock_llm.assert_called_once()
    assert ctx["answer"] == "LLM summary"
    assert ctx["agent_result"].confidence >= 0.9


@pytest.mark.asyncio
async def test_summarizer_agent_skips_llm_when_no_content():
    """Summarizer should not call LLM when there's nothing to summarize."""
    ctx = _make_ctx("Summarize")
    with (
        patch(_SETTINGS_PATCH, "sk-fake-key"),
        patch(_LLM_PATCH, new_callable=AsyncMock) as mock_llm,
    ):
        ctx = await AGENT_REGISTRY["summarizer"].run(ctx)

    mock_llm.assert_not_called()
    assert ctx["agent_result"].confidence == 0.3


@pytest.mark.asyncio
async def test_planner_agent_calls_llm_when_key_is_set():
    ctx = _make_ctx("Build a microservices architecture")
    with (
        patch(_SETTINGS_PATCH, "sk-fake-key"),
        patch(_LLM_PATCH, new_callable=AsyncMock, return_value="LLM plan") as mock_llm,
    ):
        ctx = await AGENT_REGISTRY["planner"].run(ctx)

    mock_llm.assert_called_once()
    assert ctx["answer"] == "LLM plan"
    assert ctx["agent_result"].confidence >= 0.8


@pytest.mark.asyncio
async def test_escalation_agent_calls_llm_when_key_is_set():
    ctx = _make_ctx("I am angry and want to escalate this")
    with (
        patch(_SETTINGS_PATCH, "sk-fake-key"),
        patch(_LLM_PATCH, new_callable=AsyncMock, return_value="LLM escalation response") as mock_llm,
    ):
        ctx = await AGENT_REGISTRY["escalation"].run(ctx)

    mock_llm.assert_called_once()
    assert ctx["answer"] == "LLM escalation response"
    # Escalation always sets these regardless of LLM path
    assert ctx["escalated"] is True
    assert ctx["agent_result"].escalation_required is True
    assert ctx["agent_result"].confidence == 1.0


@pytest.mark.asyncio
async def test_llm_reasoning_summary_reflects_path():
    ctx = _make_ctx("How does this work?", retrieval_context="Some docs here.")
    with (
        patch(_SETTINGS_PATCH, "sk-fake-key"),
        patch(_LLM_PATCH, new_callable=AsyncMock, return_value="LLM research answer"),
    ):
        ctx = await AGENT_REGISTRY["research"].run(ctx)

    result: AgentResult = ctx["agent_result"]
    assert "llm" in result.reasoning_summary
    assert "retrieval" in result.reasoning_summary


@pytest.mark.asyncio
async def test_fallback_reasoning_summary_reflects_path():
    ctx = _make_ctx("How does this work?", retrieval_context="Some docs here.")
    with patch(_SETTINGS_PATCH, ""):
        ctx = await AGENT_REGISTRY["research"].run(ctx)

    result: AgentResult = ctx["agent_result"]
    assert "deterministic" in result.reasoning_summary
    assert "retrieval" in result.reasoning_summary


@pytest.mark.asyncio
async def test_chat_endpoint_still_works_without_api_key():
    """Full pipeline must succeed even when OpenAI key is absent."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/chat", json=_payload("Help me fix a bug"))
    assert r.status_code == 200
    data = r.json()
    assert data["selected_agent"] == "support"
    assert len(data["answer"]) > 0
    assert "confidence" in data


@pytest.mark.asyncio
async def test_chat_endpoint_with_mocked_llm():
    """Full pipeline with mocked LLM should return the LLM answer."""
    with (
        patch(_SETTINGS_PATCH, "sk-fake-key"),
        patch(_LLM_PATCH, new_callable=AsyncMock, return_value="Mocked LLM answer for chat"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/chat", json=_payload("Hello support"))
    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == "Mocked LLM answer for chat"
    assert data["confidence"] >= 0.75
