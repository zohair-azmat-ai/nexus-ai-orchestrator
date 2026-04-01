"""
Tests for Phase 3 Step 3 — Tool framework and agent tool usage.

Covers:
  - ToolRegistry: register, get, list_tools, overwrite warning
  - BaseTool.call(): log events (tool.called, tool.result, tool.error)
  - All 5 tool execute() implementations (with mocked dependencies)
  - Agent tool wiring: _call_tool appends to ctx["tools_used"]
  - Chat endpoint returns tools_used in the response
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from httpx import AsyncClient, ASGITransport

from app.main import app


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_ctx(**overrides):
    from app.schemas.chat import ChatRequest
    request = ChatRequest(
        user_id="u1",
        session_id="s1",
        message="test message",
    )
    base = {
        "correlation_id": "cid-test",
        "request": request,
        "db": None,
        "conversation_id": None,
        "memory": {},
        "retrieval_results": [],
        "retrieval_context": "",
        "selected_agent": "support",
        "answer": "",
        "confidence": 0.0,
        "memory_used": False,
        "retrieval_used": False,
        "escalated": False,
        "events": [],
        "agent_result": None,
        "tools_used": [],
    }
    base.update(overrides)
    return base


# ─── ToolRegistry tests ───────────────────────────────────────────────────────

class TestToolRegistry:
    def setup_method(self):
        from app.services.tools.registry import ToolRegistry
        self.registry = ToolRegistry()

    def _make_tool(self, name="test_tool"):
        from app.services.tools.base_tool import BaseTool

        class _DummyTool(BaseTool):
            async def execute(self, **kwargs):
                return {"ok": True}

        t = _DummyTool()
        t.name = name
        return t

    def test_register_and_get(self):
        tool = self._make_tool("alpha")
        self.registry.register(tool)
        assert self.registry.get("alpha") is tool

    def test_get_missing_returns_none(self):
        assert self.registry.get("nonexistent") is None

    def test_list_tools_returns_descriptors(self):
        t1 = self._make_tool("a")
        t1.description = "tool a"
        t2 = self._make_tool("b")
        t2.description = "tool b"
        self.registry.register(t1)
        self.registry.register(t2)
        names = [d["name"] for d in self.registry.list_tools()]
        assert "a" in names
        assert "b" in names

    def test_len(self):
        self.registry.register(self._make_tool("x"))
        self.registry.register(self._make_tool("y"))
        assert len(self.registry) == 2

    def test_contains(self):
        self.registry.register(self._make_tool("z"))
        assert "z" in self.registry
        assert "missing" not in self.registry

    def test_overwrite_replaces_tool(self):
        t1 = self._make_tool("dup")
        t2 = self._make_tool("dup")
        self.registry.register(t1)
        self.registry.register(t2)
        assert self.registry.get("dup") is t2

    def test_global_registry_has_5_tools(self):
        import app.services.tools  # ensures registration  # noqa: F401
        from app.services.tools.registry import tool_registry
        assert len(tool_registry) >= 5


# ─── BaseTool.call() logging ──────────────────────────────────────────────────

class TestBaseToolLogging:
    def _make_simple_tool(self, execute_fn=None, fail=False):
        from app.services.tools.base_tool import BaseTool

        class _T(BaseTool):
            name = "log_test_tool"

            async def execute(self_, **kwargs):
                if fail:
                    raise RuntimeError("boom")
                return {"value": 42}

        return _T()

    @pytest.mark.asyncio
    async def test_call_logs_called_and_result(self):
        tool = self._make_simple_tool()
        with patch("app.services.tools.base_tool.logger") as mock_log:
            result = await tool.call(foo="bar")
        assert result == {"value": 42}
        logged_events = [c.args[0] for c in mock_log.info.call_args_list]
        assert "tool.called" in logged_events
        assert "tool.result" in logged_events

    @pytest.mark.asyncio
    async def test_call_logs_error_and_reraises(self):
        tool = self._make_simple_tool(fail=True)
        with patch("app.services.tools.base_tool.logger") as mock_log:
            with pytest.raises(RuntimeError, match="boom"):
                await tool.call()
        logged_events = [c.args[0] for c in mock_log.error.call_args_list]
        assert "tool.error" in logged_events


# ─── Individual tool execute() tests ─────────────────────────────────────────

class TestSearchKnowledgeBaseTool:
    @pytest.mark.asyncio
    async def test_execute_returns_results(self):
        from app.services.tools.search_knowledge_base import search_knowledge_base_tool

        mock_results = [{"text": "doc1", "score": 0.9}]
        with patch(
            "app.services.retrieval.search.semantic_search.search",
            new=AsyncMock(return_value=mock_results),
        ), patch(
            "app.services.retrieval.search.semantic_search.format_context",
            return_value="formatted context",
        ):
            result = await search_knowledge_base_tool.execute(query="what is X")

        assert result["count"] == 1
        assert result["context"] == "formatted context"
        assert result["query"] == "what is X"
        assert result["results"] == mock_results

    @pytest.mark.asyncio
    async def test_execute_empty_results(self):
        from app.services.tools.search_knowledge_base import search_knowledge_base_tool

        with patch(
            "app.services.retrieval.search.semantic_search.search",
            new=AsyncMock(return_value=[]),
        ):
            result = await search_knowledge_base_tool.execute(query="nothing")

        assert result["count"] == 0
        assert result["context"] == ""


class TestSummarizeConversationTool:
    @pytest.mark.asyncio
    async def test_execute_returns_summary(self):
        from app.services.tools.summarize_conversation import summarize_conversation_tool

        messages = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
        with patch(
            "app.services.memory.summarizer.conversation_summarizer.summarize",
            new=AsyncMock(return_value="short summary"),
        ):
            result = await summarize_conversation_tool.execute(messages=messages)

        assert result["summary"] == "short summary"
        assert result["source_count"] == 2


class TestTriggerEscalationTool:
    @pytest.mark.asyncio
    async def test_execute_returns_escalation_payload(self):
        from app.services.tools.trigger_escalation import trigger_escalation_tool

        result = await trigger_escalation_tool.execute(
            user_id="u99", reason="legal concern", conversation_id="conv-1"
        )
        assert result["escalated"] is True
        assert result["user_id"] == "u99"
        assert result["reason"] == "legal concern"
        assert result["status"] == "pending_human_review"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_execute_defaults_conversation_id(self):
        from app.services.tools.trigger_escalation import trigger_escalation_tool

        result = await trigger_escalation_tool.execute(user_id="u1", reason="urgent")
        assert result["conversation_id"] == ""


class TestGetUserContextTool:
    @pytest.mark.asyncio
    async def test_execute_with_summary_and_messages(self):
        from app.services.tools.get_user_context import get_user_context_tool

        mock_summary = MagicMock()
        mock_summary.summary_text = "past context"
        mock_msg = MagicMock()
        mock_msg.role = "user"
        mock_msg.content = "hello"

        with patch("app.db.crud.get_latest_conversation_summary", new=AsyncMock(return_value=mock_summary)), \
             patch("app.db.crud.list_recent_messages", new=AsyncMock(return_value=[mock_msg])), \
             patch("app.core.config.settings.memory_recent_message_limit", 10):
            result = await get_user_context_tool.execute(
                db=MagicMock(), conversation_id="c1", user_id="u1"
            )

        assert result["summary_text"] == "past context"
        assert len(result["recent_messages"]) == 1
        assert result["memory_used"] is True
        assert result["memory_source"] == "db"


class TestGetConversationHistoryTool:
    @pytest.mark.asyncio
    async def test_execute_returns_messages(self):
        from app.services.tools.get_conversation_history import get_conversation_history_tool

        mock_msg = MagicMock()
        mock_msg.role = "assistant"
        mock_msg.content = "sure"
        mock_msg.created_at = "2026-01-01T00:00:00"

        with patch("app.db.crud.list_recent_messages", new=AsyncMock(return_value=[mock_msg])):
            result = await get_conversation_history_tool.execute(
                db=MagicMock(), conversation_id="c1"
            )

        assert result["count"] == 1
        assert result["messages"][0]["role"] == "assistant"


# ─── Agent tool wiring tests ──────────────────────────────────────────────────

class TestAgentToolWiring:
    """Verify that each agent calls the correct tool and populates tools_used."""

    @pytest.mark.asyncio
    async def test_support_agent_calls_get_user_context(self):
        from app.services.agents.support_agent import SupportAgent

        agent = SupportAgent()
        mock_db = MagicMock()
        ctx = _make_ctx(
            db=mock_db,
            conversation_id="conv-1",
        )
        tool_return = {
            "summary_text": "ctx summary",
            "recent_messages": [],
            "memory_used": True,
            "memory_source": "db",
            "message_count": 0,
            "user_id": "u1",
        }
        with patch.object(agent, "_call_tool", new=AsyncMock(return_value=tool_return)) as mock_tool, \
             patch("app.core.config.settings.openai_api_key", ""):
            ctx = await agent.run(ctx)

        mock_tool.assert_called_once()
        assert mock_tool.call_args[0][1] == "get_user_context"

    @pytest.mark.asyncio
    async def test_support_agent_skips_tool_without_db(self):
        from app.services.agents.support_agent import SupportAgent

        agent = SupportAgent()
        ctx = _make_ctx(db=None, conversation_id=None)
        with patch.object(agent, "_call_tool", new=AsyncMock()) as mock_tool, \
             patch("app.core.config.settings.openai_api_key", ""):
            ctx = await agent.run(ctx)

        mock_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_research_agent_calls_search_when_empty_retrieval(self):
        from app.services.agents.research_agent import ResearchAgent

        agent = ResearchAgent()
        ctx = _make_ctx(retrieval_results=[], retrieval_context="")
        tool_return = {"results": [{"text": "doc"}], "context": "kb context", "count": 1, "query": "test"}
        with patch.object(agent, "_call_tool", new=AsyncMock(return_value=tool_return)) as mock_tool, \
             patch("app.core.config.settings.openai_api_key", ""):
            ctx = await agent.run(ctx)

        mock_tool.assert_called_once()
        assert mock_tool.call_args[0][1] == "search_knowledge_base"

    @pytest.mark.asyncio
    async def test_research_agent_skips_search_with_existing_retrieval(self):
        from app.services.agents.research_agent import ResearchAgent

        agent = ResearchAgent()
        ctx = _make_ctx(retrieval_results=[{"text": "existing"}], retrieval_context="already there")
        with patch.object(agent, "_call_tool", new=AsyncMock()) as mock_tool, \
             patch("app.core.config.settings.openai_api_key", ""):
            ctx = await agent.run(ctx)

        mock_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_summarizer_agent_calls_summarize_conversation(self):
        from app.services.agents.summarizer_agent import SummarizerAgent

        agent = SummarizerAgent()
        ctx = _make_ctx(
            memory={"recent_messages": [{"role": "user", "content": "hi"}]},
        )
        tool_return = {"summary": "nice summary", "source_count": 1}
        with patch.object(agent, "_call_tool", new=AsyncMock(return_value=tool_return)) as mock_tool, \
             patch("app.core.config.settings.openai_api_key", ""):
            ctx = await agent.run(ctx)

        mock_tool.assert_called_once()
        assert mock_tool.call_args[0][1] == "summarize_conversation"

    @pytest.mark.asyncio
    async def test_summarizer_agent_skips_tool_without_recent_messages(self):
        from app.services.agents.summarizer_agent import SummarizerAgent

        agent = SummarizerAgent()
        ctx = _make_ctx(memory={})
        with patch.object(agent, "_call_tool", new=AsyncMock()) as mock_tool, \
             patch("app.core.config.settings.openai_api_key", ""):
            ctx = await agent.run(ctx)

        mock_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_planner_agent_calls_search_when_empty_retrieval(self):
        from app.services.agents.planner_agent import PlannerAgent

        agent = PlannerAgent()
        ctx = _make_ctx(retrieval_results=[], retrieval_context="")
        tool_return = {"results": [], "context": "plan context", "count": 0, "query": "plan"}
        with patch.object(agent, "_call_tool", new=AsyncMock(return_value=tool_return)) as mock_tool, \
             patch("app.core.config.settings.openai_api_key", ""):
            ctx = await agent.run(ctx)

        mock_tool.assert_called_once()
        assert mock_tool.call_args[0][1] == "search_knowledge_base"

    @pytest.mark.asyncio
    async def test_planner_agent_skips_search_with_existing_retrieval(self):
        from app.services.agents.planner_agent import PlannerAgent

        agent = PlannerAgent()
        ctx = _make_ctx(retrieval_results=[{"text": "ref"}], retrieval_context="existing")
        with patch.object(agent, "_call_tool", new=AsyncMock()) as mock_tool, \
             patch("app.core.config.settings.openai_api_key", ""):
            ctx = await agent.run(ctx)

        mock_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_escalation_agent_always_calls_trigger_escalation(self):
        from app.services.agents.escalation_agent import EscalationAgent

        agent = EscalationAgent()
        ctx = _make_ctx()
        ctx["request"].message = "I want to sue you"
        tool_return = {
            "escalated": True,
            "user_id": "u1",
            "reason": "legal concern",
            "conversation_id": "",
            "timestamp": "2026-01-01T00:00:00",
            "status": "pending_human_review",
        }
        with patch.object(agent, "_call_tool", new=AsyncMock(return_value=tool_return)) as mock_tool, \
             patch("app.core.config.settings.openai_api_key", ""):
            ctx = await agent.run(ctx)

        mock_tool.assert_called_once()
        assert mock_tool.call_args[0][1] == "trigger_escalation"
        assert ctx["agent_result"].notes.get("escalated") is True

    @pytest.mark.asyncio
    async def test_call_tool_appends_to_tools_used(self):
        from app.services.agents.base import BaseAgent

        class _TestAgent(BaseAgent):
            name = "test"
            async def run(self, ctx):
                return ctx

        agent = _TestAgent()
        ctx = _make_ctx()

        import app.services.tools  # noqa: F401
        from app.services.tools.registry import tool_registry

        with patch.object(tool_registry, "get") as mock_get:
            mock_tool = MagicMock()
            mock_tool.call = AsyncMock(return_value={"ok": True})
            mock_get.return_value = mock_tool

            result = await agent._call_tool(ctx, "fake_tool", key="val")

        assert result == {"ok": True}
        assert "fake_tool" in ctx["tools_used"]

    @pytest.mark.asyncio
    async def test_call_tool_returns_none_when_not_found(self):
        from app.services.agents.base import BaseAgent

        class _TestAgent(BaseAgent):
            name = "test"
            async def run(self, ctx):
                return ctx

        agent = _TestAgent()
        ctx = _make_ctx()

        import app.services.tools  # noqa: F401
        from app.services.tools.registry import tool_registry

        with patch.object(tool_registry, "get", return_value=None):
            result = await agent._call_tool(ctx, "missing_tool")

        assert result is None
        assert ctx["tools_used"] == []

    @pytest.mark.asyncio
    async def test_call_tool_returns_none_on_exception(self):
        from app.services.agents.base import BaseAgent

        class _TestAgent(BaseAgent):
            name = "test"
            async def run(self, ctx):
                return ctx

        agent = _TestAgent()
        ctx = _make_ctx()

        import app.services.tools  # noqa: F401
        from app.services.tools.registry import tool_registry

        mock_tool = MagicMock()
        mock_tool.call = AsyncMock(side_effect=RuntimeError("kaboom"))

        with patch.object(tool_registry, "get", return_value=mock_tool):
            result = await agent._call_tool(ctx, "bad_tool")

        assert result is None
        assert ctx["tools_used"] == []


# ─── Chat endpoint tools_used propagation ────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_response_includes_tools_used():
    """tools_used must be present (possibly empty) in the ChatResponse."""
    with patch("app.services.retrieval.search.semantic_search.search", new=AsyncMock(return_value=[])), \
         patch("app.core.config.settings.openai_api_key", ""):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/chat",
                json={
                    "user_id": "u-tool-test",
                    "session_id": "s-tool-test",
                    "message": "hello",
                },
            )

    assert response.status_code == 200
    body = response.json()
    assert "tools_used" in body
    assert isinstance(body["tools_used"], list)
