from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.memory.freshness import assess_memory_freshness, select_recent_messages
from app.services.retrieval.quality import assess_retrieval_quality


BASE_PAYLOAD = {
    "user_id": "quality-user",
    "session_id": "quality-session",
    "history": [],
    "metadata": {},
}


def _payload(message: str) -> dict:
    return {**BASE_PAYLOAD, "message": message}


def test_retrieval_quality_classifies_strong_weak_and_none():
    strong = assess_retrieval_quality(
        [
            {"text": "The architecture guide recommends modular services with API-first boundaries for scaling.", "score": 0.91, "source": "docs"},
            {"text": "The implementation guide recommends validating one milestone at a time with tests.", "score": 0.85, "source": "docs"},
        ]
    )
    weak = assess_retrieval_quality(
        [{"text": "A short deployment note mentions a possible roadmap update for staging environments.", "score": 0.66, "source": "docs"}]
    )
    none = assess_retrieval_quality(
        [{"text": "tiny", "score": 0.9, "source": "docs"}]
    )

    assert strong.quality == "strong"
    assert weak.quality == "weak"
    assert none.quality == "none"


def test_retrieval_compaction_removes_duplicate_and_noisy_chunks():
    assessment = assess_retrieval_quality(
        [
            {"text": "The deployment guide says to roll out database migrations before enabling async workers.", "score": 0.88, "source": "guide-a"},
            {"text": "The deployment guide says to roll out database migrations before enabling async workers.", "score": 0.87, "source": "guide-a"},
            {"text": "tiny", "score": 0.91, "source": "guide-b"},
            {"text": "The roadmap guide recommends verifying observability signals before production rollout.", "score": 0.84, "source": "guide-c"},
        ]
    )

    assert assessment.compaction_applied is True
    assert len(assessment.compacted_results) == 2
    assert "tiny" not in assessment.compacted_context


def test_memory_freshness_marks_stale_summary_and_compacts_recent_messages():
    recent_messages = [
        {"role": "assistant", "content": "I'm here to help. Please share more details."},
        {"role": "user", "content": "The deployment pipeline keeps failing in staging and we need next steps before tomorrow."},
        {"role": "assistant", "content": "Contact support if the problem persists."},
        {"role": "user", "content": "We also need to confirm whether the roadmap should change because of this blocker."},
    ]
    selected, compacted = select_recent_messages(recent_messages, limit=2)
    freshness = assess_memory_freshness(
        summary_text="Earlier summary of the conversation.",
        summary_version=1,
        source_message_count=2,
        total_message_count=9,
        recent_messages=recent_messages,
        selected_recent_messages=selected,
    )

    assert compacted is True
    assert len(selected) == 2
    assert freshness.freshness == "stale"
    assert freshness.refresh_recommended is True


@pytest.mark.asyncio
async def test_retrieval_is_skipped_when_memory_is_sufficient():
    memory = {
        "summary_text": "We were discussing a login issue and the current workaround.",
        "recent_messages": [{"role": "user", "content": "Can you remind me what we covered?"}],
        "memory_used": True,
        "memory_source": "db",
        "memory_freshness": "fresh",
        "summary_refresh_recommended": False,
        "context_compaction_applied": False,
    }
    search_mock = AsyncMock(return_value=[])
    with (
        patch("app.services.memory.manager.memory_manager.load", new=AsyncMock(return_value=memory)),
        patch("app.services.retrieval.search.semantic_search.search", new=search_mock),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/chat", json=_payload("What did we just discuss?"))

    assert response.status_code == 200
    body = response.json()
    assert body["retrieval_used"] is False
    assert body["retrieval_quality"] == "none"
    assert body["memory_freshness"] == "fresh"
    assert "memory" in body["context_sources_used"]
    assert search_mock.await_count == 0


@pytest.mark.asyncio
async def test_weak_retrieval_produces_cautious_answer_and_metadata():
    weak_results = [
        {
            "text": "A deployment note suggests reviewing staging environment settings before rollout because some failures were reported.",
            "score": 0.66,
            "source": "docs",
        }
    ]
    with patch("app.services.retrieval.search.semantic_search.search", new=AsyncMock(return_value=weak_results)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/chat", json=_payload("Analyze these docs for deployment risk"))

    assert response.status_code == 200
    body = response.json()
    assert body["retrieval_quality"] == "weak"
    assert body["context_compaction_applied"] is False
    assert body["answer"].startswith("Based on limited retrieved evidence")
    assert body["event_summary"]["retrieval_quality"] == "weak"


@pytest.mark.asyncio
async def test_trace_logs_quality_and_freshness_events():
    stale_memory = {
        "summary_text": "Older summary that does not include the latest blocker.",
        "recent_messages": [
            {"role": "user", "content": "The production rollout is blocked and we need next steps today."},
            {"role": "user", "content": "This may affect the roadmap and escalation path."},
        ],
        "memory_used": True,
        "memory_source": "db",
        "message_count": 2,
        "total_message_count": 10,
        "summary_version": 1,
        "source_message_count": 3,
        "memory_freshness": "stale",
        "messages_since_summary": 7,
        "high_signal_recent_count": 2,
        "summary_refresh_recommended": True,
        "context_compaction_applied": False,
    }
    noisy_results = [
        {"text": "tiny", "score": 0.92, "source": "docs"},
        {"text": "The implementation notes recommend validating recent blockers before updating the roadmap.", "score": 0.7, "source": "docs"},
        {"text": "The implementation notes recommend validating recent blockers before updating the roadmap.", "score": 0.69, "source": "docs"},
    ]
    with (
        patch("app.services.memory.manager.memory_manager.load", new=AsyncMock(return_value=stale_memory)),
        patch("app.services.retrieval.search.semantic_search.search", new=AsyncMock(return_value=noisy_results)),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-Correlation-ID": "trace-quality-001"},
        ) as client:
            response = await client.post("/api/v1/chat", json=_payload("Analyze docs and plan the next steps"))
            assert response.status_code == 200
            trace_response = await client.get("/api/v1/observability/trace/trace-quality-001")

    events = {event["event_type"] for event in trace_response.json()["events"]}
    assert "retrieval.quality.assessed" in events
    assert "retrieval.context.compacted" in events
    assert "memory.freshness.assessed" in events
    assert "memory.summary.refresh_recommended" in events
    assert "response.grounding.mode" in events
