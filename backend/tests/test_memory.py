"""
Tests for Phase 2 Step 3 — DB-backed memory persistence.

All tests run against SQLite in-memory via the conftest override_db fixture.
OpenAI is mocked so no live services are required.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401
from app.db.postgres import Base, get_db
from app.main import app
from app.db import crud
from app.services.memory.manager import memory_manager
from app.services.memory.rules import memory_rules
from app.services.memory.summarizer import conversation_summarizer

SQLITE_URL = "sqlite+aiosqlite:///:memory:"

CHAT_PAYLOAD = {
    "user_id": "user-mem-001",
    "session_id": "session-mem-001",
    "message": "Tell me about Nexus AI.",
    "history": [],
    "metadata": {},
}


# ─── Helper ───────────────────────────────────────────────────────────────────

async def _make_db_session():
    """Create a standalone in-memory SQLite session for unit tests."""
    engine = create_async_engine(SQLITE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


# ─── Memory Rules ─────────────────────────────────────────────────────────────

def test_memory_rules_should_summarize_at_threshold():
    trigger = memory_rules.summarize_after_turns
    assert not memory_rules.should_summarize(trigger - 1)
    assert memory_rules.should_summarize(trigger)
    assert memory_rules.should_summarize(trigger + 5)


def test_memory_rules_reads_from_settings():
    from app.core.config import settings
    assert memory_rules.summarize_after_turns == settings.memory_summary_trigger_count
    assert memory_rules.recent_message_limit == settings.memory_recent_message_limit


# ─── Summarizer ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summarizer_empty_history_returns_empty():
    result = await conversation_summarizer.summarize([])
    assert result == ""


@pytest.mark.asyncio
async def test_summarizer_deterministic_fallback():
    """When LLM is disabled, should produce a deterministic summary."""
    history = [
        {"role": "user", "content": "What is Nexus AI?"},
        {"role": "assistant", "content": "It is a RAG platform."},
    ]
    with patch("app.services.memory.summarizer.settings") as mock_settings:
        mock_settings.memory_enable_llm_summarization = False
        mock_settings.openai_api_key = ""
        result = await conversation_summarizer.summarize(history)

    assert "Nexus AI" in result
    assert len(result) > 0


@pytest.mark.asyncio
async def test_summarizer_llm_path():
    """When LLM is enabled and API key is set, should call openai_client.complete."""
    history = [{"role": "user", "content": "Summarize this"}, {"role": "assistant", "content": "Done"}]

    with (
        patch("app.services.memory.summarizer.settings") as mock_settings,
        patch("app.services.memory.summarizer.ConversationSummarizer._llm_summarize", new_callable=AsyncMock) as mock_llm,
    ):
        mock_settings.memory_enable_llm_summarization = True
        mock_settings.openai_api_key = "sk-fake"
        mock_llm.return_value = "LLM-generated summary."
        result = await conversation_summarizer.summarize(history)

    mock_llm.assert_called_once()
    assert result == "LLM-generated summary."


@pytest.mark.asyncio
async def test_summarizer_llm_fallback_on_error():
    """If LLM call raises, should fall back to deterministic summary."""
    history = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]

    with (
        patch("app.services.memory.summarizer.settings") as mock_settings,
        patch("app.services.memory.summarizer.ConversationSummarizer._llm_summarize", new_callable=AsyncMock) as mock_llm,
    ):
        mock_settings.memory_enable_llm_summarization = True
        mock_settings.openai_api_key = "sk-fake"
        mock_llm.side_effect = RuntimeError("OpenAI unavailable")
        result = await conversation_summarizer.summarize(history)

    assert len(result) > 0  # deterministic fallback ran


# ─── CRUD — Summary helpers ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crud_upsert_summary_creates_new():
    engine, factory = await _make_db_session()
    async with factory() as db:
        # need a conversation to satisfy FK
        conv = await crud.create_conversation(db, "user-x")
        await db.commit()
        summary = await crud.upsert_conversation_summary(
            db,
            conversation_id=conv.id,
            user_id="user-x",
            summary_text="First summary.",
            source_message_count=5,
        )
        await db.commit()
        assert summary.summary_text == "First summary."
        assert summary.summary_version == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_crud_upsert_summary_updates_existing():
    engine, factory = await _make_db_session()
    async with factory() as db:
        conv = await crud.create_conversation(db, "user-y")
        await db.commit()
        await crud.upsert_conversation_summary(db, conv.id, "user-y", "v1", 5)
        await db.commit()
        updated = await crud.upsert_conversation_summary(db, conv.id, "user-y", "v2", 10)
        await db.commit()
        assert updated.summary_text == "v2"
        assert updated.summary_version == 2

    await engine.dispose()


@pytest.mark.asyncio
async def test_crud_list_recent_messages_respects_limit():
    engine, factory = await _make_db_session()
    async with factory() as db:
        conv = await crud.create_conversation(db, "user-z")
        for i in range(8):
            await crud.create_message(db, conv.id, "user", f"message {i}")
        await db.commit()
        recent = await crud.list_recent_messages(db, conv.id, limit=3)
        assert len(recent) == 3
        # Should be last 3, returned oldest-first
        assert recent[-1].content == "message 7"

    await engine.dispose()


# ─── Memory Manager ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_memory_manager_load_returns_empty_for_new_conversation():
    engine, factory = await _make_db_session()
    async with factory() as db:
        conv = await crud.create_conversation(db, "user-new")
        await db.commit()
        ctx = await memory_manager.load(db, conv.id, "user-new")

    assert ctx["memory_used"] is False
    assert ctx["summary_text"] is None
    assert ctx["recent_messages"] == []
    await engine.dispose()


@pytest.mark.asyncio
async def test_memory_manager_load_returns_context_when_messages_exist():
    engine, factory = await _make_db_session()
    async with factory() as db:
        conv = await crud.create_conversation(db, "user-ctx")
        await crud.create_message(db, conv.id, "user", "Hello")
        await crud.create_message(db, conv.id, "assistant", "Hi there")
        await db.commit()
        ctx = await memory_manager.load(db, conv.id, "user-ctx")

    assert ctx["memory_used"] is True
    assert len(ctx["recent_messages"]) == 2
    await engine.dispose()


@pytest.mark.asyncio
async def test_memory_manager_load_includes_summary_when_present():
    engine, factory = await _make_db_session()
    async with factory() as db:
        conv = await crud.create_conversation(db, "user-sum")
        await db.commit()
        await crud.upsert_conversation_summary(db, conv.id, "user-sum", "Great summary", 10)
        await db.commit()
        ctx = await memory_manager.load(db, conv.id, "user-sum")

    assert ctx["summary_text"] == "Great summary"
    assert ctx["memory_used"] is True
    await engine.dispose()


# ─── Integration: chat with memory stage ─────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_memory_stage_runs_without_error():
    """Full chat request should succeed with DB-backed memory stage."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert "memory_used" in data


@pytest.mark.asyncio
async def test_chat_memory_used_after_second_turn():
    """On the second turn the memory stage should detect existing messages."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
        conv_id = first.json()["conversation_id"]

        second = await client.post(
            "/api/v1/chat",
            json={**CHAT_PAYLOAD, "message": "What did I just ask?", "conversation_id": conv_id},
        )

    data = second.json()
    assert data["memory_used"] is True


@pytest.mark.asyncio
async def test_memory_api_returns_200_for_known_user():
    """GET /api/v1/memory/{user_id} should return 200 after at least one chat."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
        response = await client.get(f"/api/v1/memory/{CHAT_PAYLOAD['user_id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == CHAT_PAYLOAD["user_id"]
    assert "session_count" in data


@pytest.mark.asyncio
async def test_summary_triggered_at_threshold():
    """Once messages_count reaches the threshold, a summary should be persisted."""
    from app.core.config import settings

    # Patch trigger to 2 so one chat (2 messages) fires it
    with patch.object(settings, "memory_summary_trigger_count", 2):
        with patch(
            "app.services.memory.summarizer.ConversationSummarizer.summarize",
            new_callable=AsyncMock,
            return_value="Auto-generated summary.",
        ) as mock_summarize:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)

        assert response.status_code == 200
        mock_summarize.assert_called_once()
