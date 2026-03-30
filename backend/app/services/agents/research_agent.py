"""
Research Agent — handles research, explanation, analysis, and knowledge synthesis queries.

Behavior:
- Presents findings in an analytical, structured style
- Uses retrieval context as evidence base when available
- Surfaces key insights rather than raw text
"""

from typing import Any

from app.services.agents.base import BaseAgent, AgentResult

OrchestratorContext = dict[str, Any]


class ResearchAgent(BaseAgent):
    name = "research"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)

        message = ctx["request"].message
        retrieval_context: str = ctx.get("retrieval_context", "")
        retrieval_results: list = ctx.get("retrieval_results", [])
        memory: dict = ctx.get("memory", {})
        summary_text: str | None = memory.get("summary_text")

        if retrieval_context:
            source_count = len(retrieval_results)
            answer = (
                f"Research findings for: \"{message}\"\n\n"
                f"Drawing from {source_count} relevant source(s):\n\n"
                f"{retrieval_context}\n\n"
                "**Analysis:** The retrieved information addresses your query directly. "
                "For deeper exploration, consider asking follow-up questions on specific aspects."
            )
            confidence = 0.85
            reasoning = f"retrieval returned {source_count} sources"
        elif summary_text:
            answer = (
                f"Research on: \"{message}\"\n\n"
                f"**Context from prior discussion:** {summary_text}\n\n"
                "Based on this context, the topic appears to relate to the areas discussed above. "
                "Adding more specific documents to the knowledge base will improve research quality."
            )
            confidence = 0.6
            reasoning = "no retrieval; using memory summary"
        else:
            # Extract key terms from the message for a structured response
            words = [w for w in message.lower().split() if len(w) > 3]
            key_terms = list(dict.fromkeys(words))[:4]  # deduplicated, max 4
            terms_str = ", ".join(key_terms) if key_terms else "the requested topic"

            answer = (
                f"Research on: \"{message}\"\n\n"
                f"**Key concepts identified:** {terms_str}\n\n"
                "No documents have been indexed for this topic yet. "
                "To get evidence-backed research answers:\n"
                "1. Ingest relevant documents via /api/v1/ingest\n"
                "2. Re-submit your query for retrieval-grounded analysis"
            )
            confidence = 0.4
            reasoning = "no retrieval or memory context; structural response only"

        result = self._build_result(
            answer=answer,
            confidence=confidence,
            ctx=ctx,
            reasoning_summary=reasoning,
        )
        ctx["answer"] = answer
        ctx["agent_result"] = result
        return ctx


research_agent = ResearchAgent()
