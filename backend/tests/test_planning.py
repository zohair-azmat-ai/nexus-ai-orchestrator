from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


BASE_PAYLOAD = {
    "user_id": "plan-user",
    "session_id": "plan-session",
    "history": [],
    "metadata": {},
}


def _payload(message: str) -> dict:
    return {**BASE_PAYLOAD, "message": message}


@pytest.mark.asyncio
async def test_simple_request_stays_single_step():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json=_payload("Hello there"))

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "single_step"
    assert body["executed_steps_count"] == 1
    assert body["skipped_steps_count"] == 0
    assert body["final_agent"] == body["selected_agent"] == "support"
    assert body["execution_plan_summary"]["execution_mode"] == "single_step"
    assert body["tools_planned"] == []
    assert len(body["execution_plan_summary"]["steps"]) == 1


@pytest.mark.asyncio
async def test_retrieval_is_skipped_when_context_already_exists():
    fake_results = [{"text": "Architecture docs", "score": 0.9, "source": "docs"}]
    fake_context = "Architecture docs say to implement the API incrementally."
    with (
        patch("app.services.retrieval.search.semantic_search.search", new=AsyncMock(return_value=fake_results)),
        patch("app.services.retrieval.search.semantic_search.format_context", return_value=fake_context),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json=_payload("Analyze docs and make an implementation roadmap"),
            )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "multi_step"
    assert body["executed_steps_count"] == 1
    assert body["skipped_steps_count"] == 1
    steps = body["execution_plan_summary"]["steps"]
    assert steps[0]["target"] == "research"
    assert steps[0]["status"] == "skipped"
    assert "Retrieval context already provides evidence" in (steps[0]["skip_reason"] or "")
    assert steps[1]["target"] == "planner"
    assert steps[1]["depends_on"] == [steps[0]["step_id"]]


@pytest.mark.asyncio
async def test_summarizer_step_is_skipped_when_existing_summary_is_enough():
    memory = {
        "summary_text": "Customer reported a recurring login issue and wants a short recap.",
        "recent_messages": [],
        "memory_used": True,
        "memory_source": "db",
        "message_count": 0,
    }
    with patch("app.services.memory.manager.memory_manager.load", new=AsyncMock(return_value=memory)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/chat", json=_payload("Give me a brief recap"))

    assert response.status_code == 200
    body = response.json()
    assert body["final_agent"] == "system"
    assert body["skipped_steps_count"] == 1
    steps = body["execution_plan_summary"]["steps"]
    assert steps[0]["target"] == "use_stored_summary"
    assert steps[0]["status"] == "completed"
    assert steps[1]["target"] == "summarizer"
    assert steps[1]["status"] == "skipped"
    assert "Stored summary already satisfies" in (steps[1]["skip_reason"] or "")


@pytest.mark.asyncio
async def test_escalation_short_circuits_other_steps():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json=_payload("This is urgent and legal, please escalate immediately"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "single_step"
    assert body["executed_steps_count"] == 1
    assert body["final_agent"] == "escalation"
    assert [step["target"] for step in body["execution_plan_summary"]["steps"]] == ["escalation"]
    assert body["tools_planned"] == ["trigger_escalation"]


@pytest.mark.asyncio
async def test_research_planner_chain_includes_kb_search_when_needed():
    with patch("app.services.retrieval.search.semantic_search.search", new=AsyncMock(return_value=[])):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json=_payload("Analyze docs and make an implementation roadmap"),
            )

    assert response.status_code == 200
    body = response.json()
    steps = body["execution_plan_summary"]["steps"]
    assert [step["target"] for step in steps] == ["research", "planner"]
    assert "search_knowledge_base" in steps[0]["recommended_tools"]
    assert "search_knowledge_base" in steps[1]["recommended_tools"]
    assert "search_knowledge_base" in body["tools_planned"]


@pytest.mark.asyncio
async def test_step_dependencies_are_respected_in_plan():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json=_payload("Summarize these findings and give me next steps"),
        )

    assert response.status_code == 200
    steps = response.json()["execution_plan_summary"]["steps"]
    assert steps[1]["depends_on"] == [steps[0]["step_id"]]
    assert steps[2]["depends_on"] == [steps[1]["step_id"]]


@pytest.mark.asyncio
async def test_skipped_steps_reflected_in_response_metadata():
    fake_results = [{"text": "Indexed docs", "score": 0.9, "source": "docs"}]
    with (
        patch("app.services.retrieval.search.semantic_search.search", new=AsyncMock(return_value=fake_results)),
        patch("app.services.retrieval.search.semantic_search.format_context", return_value="Indexed docs context"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json=_payload("Analyze docs and make an implementation roadmap"),
            )

    body = response.json()
    assert body["skipped_steps_count"] == 1
    assert body["plan_summary"]["skipped_steps_count"] == 1
    assert any(step["status"] == "skipped" for step in body["execution_plan_summary"]["steps"])
