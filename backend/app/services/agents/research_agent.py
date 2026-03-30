"""
Research Agent — handles research, explanation, analysis, and knowledge synthesis.

LLM path: analytical, evidence-based response grounded in retrieval context.
Fallback: structured key-term extraction with guidance when LLM unavailable.
"""

from typing import Any

from app.core.config import settings
from app.core.logger import get_logger
from app.services.agents.base import BaseAgent, AgentResult

OrchestratorContext = dict[str, Any]
logger = get_logger(__name__)


class ResearchAgent(BaseAgent):
    name = "research"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)

        message = ctx["request"].message
        retrieval_context: str = ctx.get("retrieval_context", "")
        retrieval_results: list = ctx.get("retrieval_results", [])
        memory: dict = ctx.get("memory", {})
        llm_used = False

        if settings.openai_api_key:
            try:
                answer = await self._llm_answer(message, retrieval_context, memory)
                llm_used = True
            except Exception as exc:
                logger.warning("research_agent.llm_failed", extra={"error": str(exc)})
                answer = self._deterministic_answer(message, retrieval_context, retrieval_results, memory)
        else:
            answer = self._deterministic_answer(message, retrieval_context, retrieval_results, memory)

        confidence = self._score_confidence(llm_used, retrieval_context, memory)
        reasoning = self._reasoning_summary(llm_used, retrieval_context, retrieval_results, memory)

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
            agent_name="research",
            message=message,
            retrieval_context=retrieval_context,
            memory=memory or None,
        )

    # ── Deterministic fallback ─────────────────────────────────────────────────

    def _deterministic_answer(
        self, message: str, retrieval_context: str, retrieval_results: list, memory: dict
    ) -> str:
        summary_text: str | None = memory.get("summary_text")

        if retrieval_context:
            source_count = len(retrieval_results)
            return (
                f"Research findings for: \"{message}\"\n\n"
                f"Drawing from {source_count} relevant source(s):\n\n"
                f"{retrieval_context}\n\n"
                "**Analysis:** The retrieved information addresses your query directly. "
                "For deeper exploration, consider asking follow-up questions on specific aspects."
            )
        elif summary_text:
            return (
                f"Research on: \"{message}\"\n\n"
                f"**Context from prior discussion:** {summary_text}\n\n"
                "Based on this context, the topic relates to the areas discussed above. "
                "Adding more specific documents to the knowledge base will improve research quality."
            )
        words = [w for w in message.lower().split() if len(w) > 3]
        key_terms = list(dict.fromkeys(words))[:4]
        terms_str = ", ".join(key_terms) if key_terms else "the requested topic"
        return (
            f"Research on: \"{message}\"\n\n"
            f"**Key concepts identified:** {terms_str}\n\n"
            "No documents have been indexed for this topic yet. "
            "To get evidence-backed research answers:\n"
            "1. Ingest relevant documents via /api/v1/ingest\n"
            "2. Re-submit your query for retrieval-grounded analysis"
        )

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _score_confidence(self, llm_used: bool, retrieval_context: str, memory: dict) -> float:
        if retrieval_context:
            return 0.95 if llm_used else 0.85
        if memory.get("summary_text"):
            return 0.78 if llm_used else 0.6
        return 0.72 if llm_used else 0.4

    def _reasoning_summary(
        self, llm_used: bool, retrieval_context: str, retrieval_results: list, memory: dict
    ) -> str:
        path = "llm" if llm_used else "deterministic fallback"
        ctx_parts = []
        if retrieval_context:
            ctx_parts.append(f"{len(retrieval_results)} retrieval source(s)")
        if memory.get("summary_text"):
            ctx_parts.append("memory summary")
        ctx_str = ", ".join(ctx_parts) if ctx_parts else "no external context"
        return f"{path}; evidence: {ctx_str}"


research_agent = ResearchAgent()
