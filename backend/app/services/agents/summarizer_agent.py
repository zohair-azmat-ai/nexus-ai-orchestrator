"""
Summarizer Agent — condenses conversation history or retrieved documents.

LLM path: uses OpenAI to produce a tight, accurate summary of available content.
Fallback: bullet-point condensation of available messages/retrieval context.
"""

from typing import Any

from app.core.config import settings
from app.core.logger import get_logger
from app.services.agents.base import BaseAgent, AgentResult

OrchestratorContext = dict[str, Any]
logger = get_logger(__name__)


class SummarizerAgent(BaseAgent):
    name = "summarizer"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)

        message = ctx["request"].message
        memory: dict = ctx.get("memory", {})
        retrieval_context: str = ctx.get("retrieval_context", "")

        # Produce a condensed summary of recent messages via tool before LLM/deterministic step
        recent_messages: list = memory.get("recent_messages", [])
        if recent_messages:
            tool_result = await self._call_tool(
                ctx, "summarize_conversation", messages=recent_messages
            )
            if tool_result and tool_result.get("summary"):
                # Inject tool-produced summary into memory so both paths can use it
                memory = {**memory, "summary_text": tool_result["summary"]}

        has_content = bool(
            memory.get("recent_messages") or memory.get("summary_text") or retrieval_context
        )
        llm_used = False

        if has_content and settings.openai_api_key:
            try:
                answer = await self._llm_answer(message, retrieval_context, memory)
                llm_used = True
            except Exception as exc:
                logger.warning("summarizer_agent.llm_failed", extra={"error": str(exc)})
                answer = self._deterministic_answer(message, retrieval_context, memory)
        else:
            answer = self._deterministic_answer(message, retrieval_context, memory)

        confidence = self._score_confidence(llm_used, has_content, memory, retrieval_context)
        reasoning = self._reasoning_summary(llm_used, memory, retrieval_context)

        result = self._build_result(
            answer=answer,
            confidence=confidence,
            ctx=ctx,
            reasoning_summary=reasoning,
        )
        ctx["answer"] = answer
        ctx["agent_result"] = result
        return ctx

    # ── LLM path ──────────────────────────────────────────────────────────────

    async def _llm_answer(self, message: str, retrieval_context: str, memory: dict) -> str:
        from app.services.llm.router import call_llm
        return await call_llm(
            agent_name="summarizer",
            message=message,
            retrieval_context=retrieval_context,
            memory=memory or None,
        )

    # ── Deterministic fallback ─────────────────────────────────────────────────

    def _deterministic_answer(self, message: str, retrieval_context: str, memory: dict) -> str:
        recent_messages: list = memory.get("recent_messages", [])
        summary_text: str | None = memory.get("summary_text")

        if recent_messages:
            bullets = "\n".join(
                f"- [{m['role'].upper()}]: {m['content'][:120]}{'...' if len(m['content']) > 120 else ''}"
                for m in recent_messages
            )
            prior = f"\n\n**Prior summary on record:** {summary_text}" if summary_text else ""
            return (
                f"**Conversation Summary** ({len(recent_messages)} recent message(s)):\n\n"
                f"{bullets}{prior}\n\n"
                "This captures the key exchanges from your recent conversation."
            )
        elif summary_text:
            return (
                f"**Stored Summary:**\n\n{summary_text}\n\n"
                "This is the most recent recorded summary of your conversation history."
            )
        elif retrieval_context:
            lines = [ln.strip() for ln in retrieval_context.splitlines() if ln.strip()]
            condensed = "\n".join(f"- {ln}" for ln in lines[:8])
            return (
                f"**Document Summary** for: \"{message}\"\n\n"
                f"{condensed}\n\n"
                "These are the key points extracted from the relevant documents."
            )
        return (
            "There is no conversation history or indexed content available to summarize.\n\n"
            "To get a summary:\n"
            "- Continue the conversation to build up history, or\n"
            "- Ingest documents via /api/v1/ingest and ask again"
        )

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _score_confidence(
        self, llm_used: bool, has_content: bool, memory: dict, retrieval_context: str
    ) -> float:
        if not has_content:
            return 0.3
        if memory.get("recent_messages"):
            return 0.95 if llm_used else 0.87
        if memory.get("summary_text"):
            return 0.92 if llm_used else 0.85
        if retrieval_context:
            return 0.88 if llm_used else 0.8
        return 0.7

    def _reasoning_summary(self, llm_used: bool, memory: dict, retrieval_context: str) -> str:
        path = "llm" if llm_used else "deterministic fallback"
        sources = []
        if memory.get("recent_messages"):
            sources.append(f"{len(memory['recent_messages'])} recent messages")
        if memory.get("summary_text"):
            sources.append("stored summary")
        if retrieval_context:
            sources.append("retrieval context")
        src_str = ", ".join(sources) if sources else "no content"
        return f"{path}; summarized: {src_str}"


summarizer_agent = SummarizerAgent()
