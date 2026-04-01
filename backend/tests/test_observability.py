from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


CHAT_PAYLOAD = {
    "user_id": "obs-user",
    "session_id": "obs-session",
    "message": "I want to escalate this issue immediately",
    "history": [],
    "metadata": {},
}


@pytest.mark.asyncio
async def test_chat_response_includes_trace_id_and_stage_timings():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"] == body["correlation_id"]
    assert response.headers["x-trace-id"] == body["trace_id"]
    assert isinstance(body["stage_timings"], dict)
    assert "intake" in body["stage_timings"]
    assert "response" in body["stage_timings"]
    assert all(value >= 0 for value in body["stage_timings"].values())


@pytest.mark.asyncio
async def test_trace_endpoint_returns_enriched_events():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        chat_response = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
        trace_id = chat_response.json()["trace_id"]
        trace_response = await client.get(f"/api/v1/observability/trace/{trace_id}")

    assert trace_response.status_code == 200
    body = trace_response.json()
    assert body["trace_id"] == trace_id
    assert body["agent_used"] == "escalation"
    assert "trigger_escalation" in body["tools_used"]
    assert "response" in body["stage_timings"]
    assert len(body["events"]) > 0

    first_event = body["events"][0]
    assert "trace_id" in first_event
    assert "stage" in first_event
    assert "component" in first_event
    assert "status" in first_event


@pytest.mark.asyncio
async def test_trace_endpoint_contains_plan_skip_and_recommendation_events():
    fake_results = [
        {"text": "Indexed docs provide a modular architecture plan for the backend services.", "score": 0.92, "source": "docs"},
        {"text": "Indexed docs also outline milestone sequencing and testing checkpoints.", "score": 0.85, "source": "docs"},
    ]
    with (
        patch("app.services.retrieval.search.semantic_search.search", new=AsyncMock(return_value=fake_results)),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-Correlation-ID": "trace-plan-skip"},
        ) as client:
            response = await client.post(
                "/api/v1/chat",
                json={
                    "user_id": "obs-user",
                    "session_id": "obs-session",
                    "message": "Analyze docs and make an implementation roadmap",
                },
            )
            assert response.status_code == 200
            trace_response = await client.get("/api/v1/observability/trace/trace-plan-skip")

    events = trace_response.json()["events"]
    event_types = [event["event_type"] for event in events]
    assert "plan.context.routed" in event_types
    assert "plan.step.skipped" in event_types

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Correlation-ID": "trace-plan-tool"},
    ) as client:
        response = await client.post(
            "/api/v1/chat",
            json={
                "user_id": "obs-user",
                "session_id": "obs-session",
                "message": "Analyze docs and make an implementation roadmap",
            },
        )
        assert response.status_code == 200
        trace_response = await client.get("/api/v1/observability/trace/trace-plan-tool")

    recommended_event_types = [event["event_type"] for event in trace_response.json()["events"]]
    assert "plan.tool.recommended" in recommended_event_types


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_request_agent_tool_and_error_counts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
        metrics_response = await client.get("/api/v1/observability/metrics")

    assert metrics_response.status_code == 200
    metrics = metrics_response.json()["metrics"]
    assert metrics["total_requests"] >= 2
    assert metrics["agent_usage"]["escalation"] >= 1
    assert metrics["tool_usage"]["trigger_escalation"] >= 1


@pytest.mark.asyncio
async def test_trace_endpoint_includes_job_events():
    ingest_result = {"document_id": "doc-1", "chunks_created": 2, "collection_name": "nexus"}
    with patch("app.services.retrieval.ingest.ingest_service.ingest", new=AsyncMock(return_value=ingest_result)):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-Correlation-ID": "trace-job-123"},
        ) as client:
            response = await client.post("/api/v1/jobs/ingest", json={"text": "hello", "source": "tests"})
            assert response.status_code == 200
            trace_response = await client.get("/api/v1/observability/trace/trace-job-123")

    body = trace_response.json()
    event_types = {event["event_type"] for event in body["events"]}
    assert "job.created" in event_types
    assert "job.started" in event_types
    assert "job.completed" in event_types


@pytest.mark.asyncio
async def test_trace_endpoint_returns_404_for_unknown_trace():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/observability/trace/missing-trace")

    assert response.status_code == 404
