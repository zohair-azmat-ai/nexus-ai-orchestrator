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
    assert body["final_agent"] == body["selected_agent"] == "support"
    assert body["execution_plan_summary"]["execution_mode"] == "single_step"
    assert len(body["execution_plan_summary"]["steps"]) == 1


@pytest.mark.asyncio
async def test_complex_request_triggers_research_then_planner_chain():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json=_payload("Analyze docs and make an implementation roadmap"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "multi_step"
    assert body["executed_steps_count"] == 2
    assert body["selected_agent"] == "planner"
    assert body["final_agent"] == "planner"
    assert [step["target"] for step in body["execution_plan_summary"]["steps"]] == ["research", "planner"]


@pytest.mark.asyncio
async def test_chained_execution_passes_outputs_into_escalation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json=_payload("Investigate this issue and tell me whether it should be escalated"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "multi_step"
    assert body["final_agent"] == "escalation"
    assert body["executed_steps_count"] == 2
    assert [step["target"] for step in body["execution_plan_summary"]["steps"]] == ["support", "escalation"]
    assert "For context, here is a summary of recent interactions" in body["answer"]


@pytest.mark.asyncio
async def test_multi_step_response_includes_execution_metadata():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json=_payload("Summarize these findings and give me next steps"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "multi_step"
    assert body["executed_steps_count"] == 3
    assert body["final_agent"] == "planner"
    assert body["execution_plan_summary"]["plan_id"]
    assert [step["target"] for step in body["execution_plan_summary"]["steps"]] == ["research", "summarizer", "planner"]


@pytest.mark.asyncio
async def test_trace_endpoint_contains_plan_step_events():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Correlation-ID": "plan-trace-123"},
    ) as client:
        chat_response = await client.post(
            "/api/v1/chat",
            json=_payload("Analyze docs and make an implementation roadmap"),
        )
        assert chat_response.status_code == 200
        trace_response = await client.get("/api/v1/observability/trace/plan-trace-123")

    assert trace_response.status_code == 200
    events = trace_response.json()["events"]
    event_types = [event["event_type"] for event in events]
    assert "plan.created" in event_types
    assert "plan.step.started" in event_types
    assert "plan.step.completed" in event_types
    assert sum(1 for event in events if event["event_type"] == "plan.step.completed") >= 2
