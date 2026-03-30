"""
Research Agent — handles research, lookup, and knowledge synthesis queries.

Responsibilities:
- Deep search across the knowledge base
- Multi-document synthesis
- Confidence scoring on results
"""

from typing import Any

from app.services.agents.base import BaseAgent

OrchestratorContext = dict[str, Any]


class ResearchAgent(BaseAgent):
    name = "research"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)
        message = ctx["request"].message

        # Phase 3: multi-step retrieval + synthesis
        ctx["answer"] = (
            f"Research results for: '{message}'. "
            "Phase 3 will perform multi-document synthesis with real retrieval."
        )
        return ctx


research_agent = ResearchAgent()
