"""
Support Agent — handles general customer support, troubleshooting, and help queries.

LLM path: grounded answer using retrieval context + memory history.
Fallback: deterministic template when OpenAI is unavailable.
"""

from typing import Any

from app.core.config import settings
from app.core.logger import get_logger
from app.services.agents.base import BaseAgent, AgentResult

OrchestratorContext = dict[str, Any]
logger = get_logger(__name__)


class SupportAgent(BaseAgent):
    name = "support"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)

        message = ctx["request"].message
        retrieval_context: str = ctx.get("retrieval_context", "")
        memory: dict = ctx.get("memory", {})
        llm_used = False

        # Enrich memory from DB via tool when a live session is available
        db = ctx.get("db")
        conversation_id = ctx.get("conversation_id")
        if db and conversation_id:
            tool_result = await self._call_tool(
                ctx,
                "get_user_context",
                db=db,
                conversation_id=conversation_id,
                user_id=ctx["request"].user_id,
            )
            if tool_result:
                memory = tool_result

        if settings.openai_api_key:
            try:
                answer = await self._llm_answer(message, retrieval_context, memory)
                llm_used = True
            except Exception as exc:
                logger.warning("support_agent.llm_failed", extra={"error": str(exc)})
                answer = self._deterministic_answer(message, retrieval_context, memory)
        else:
            answer = self._deterministic_answer(message, retrieval_context, memory)

        confidence = self._score_confidence(llm_used, retrieval_context, memory)
        reasoning = self._reasoning_summary(llm_used, retrieval_context, memory)

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
            agent_name="support",
            message=message,
            retrieval_context=retrieval_context,
            memory=memory or None,
        )

    # ── Deterministic fallback ─────────────────────────────────────────────────

    def _deterministic_answer(self, message: str, retrieval_context: str, memory: dict) -> str:
        summary_text: str | None = memory.get("summary_text")
        recent_messages: list = memory.get("recent_messages", [])

        if retrieval_context:
            return (
                "Based on our knowledge base, here is what I found:\n\n"
                f"{retrieval_context}\n\n"
                "If this doesn't fully address your issue, please share more details "
                "and I'll investigate further."
            )
        elif summary_text:
            return (
                f"Based on our conversation history: {summary_text}\n\n"
                f"Regarding your question — \"{message}\" — "
                "I recommend reviewing the relevant documentation or contacting "
                "our support team directly if the issue persists."
            )
        elif recent_messages:
            turns = len(recent_messages)
            return (
                f"I can see we've been talking for {turns} message(s). "
                f"Regarding \"{message}\": I'm here to help — could you provide "
                "more details about what you're experiencing so I can assist better?"
            )
        return (
            f"I'm here to help with: \"{message}\".\n\n"
            "To give you the most accurate support, please describe:\n"
            "1. What you were trying to do\n"
            "2. What happened instead\n"
            "3. Any error messages you saw"
        )

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _score_confidence(self, llm_used: bool, retrieval_context: str, memory: dict) -> float:
        if retrieval_context:
            return 0.95 if llm_used else 0.9
        if memory.get("summary_text") or memory.get("recent_messages"):
            return 0.82 if llm_used else 0.7
        return 0.75 if llm_used else 0.5

    def _reasoning_summary(self, llm_used: bool, retrieval_context: str, memory: dict) -> str:
        path = "llm" if llm_used else "deterministic fallback"
        ctx_parts = []
        if retrieval_context:
            ctx_parts.append("retrieval context")
        if memory.get("summary_text"):
            ctx_parts.append("memory summary")
        elif memory.get("recent_messages"):
            ctx_parts.append("recent messages")
        ctx_str = ", ".join(ctx_parts) if ctx_parts else "no external context"
        return f"{path}; used: {ctx_str}"


support_agent = SupportAgent()
