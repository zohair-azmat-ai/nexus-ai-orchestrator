"""
Support Agent — handles general customer support queries.

Responsibilities:
- Answer product/service questions
- Pull from retrieval context when available
- Escalate if confidence is low
"""

from typing import Any

from app.services.agents.base import BaseAgent

OrchestratorContext = dict[str, Any]


class SupportAgent(BaseAgent):
    name = "support"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)
        message = ctx["request"].message
        retrieval_context = ctx.get("retrieval_results", [])

        # Phase 3: build prompt with retrieval context and call OpenAI
        if retrieval_context:
            ctx["answer"] = f"Based on our knowledge base: [RAG response for '{message}']"
        else:
            ctx["answer"] = f"Support response to: '{message}'. (Phase 3 will integrate real LLM responses.)"

        return ctx


support_agent = SupportAgent()
