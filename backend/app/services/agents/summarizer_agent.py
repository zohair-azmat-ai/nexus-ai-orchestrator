"""
Summarizer Agent — condenses content or conversation into compact summaries.
"""

from typing import Any

from app.services.agents.base import BaseAgent

OrchestratorContext = dict[str, Any]


class SummarizerAgent(BaseAgent):
    name = "summarizer"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)
        history = ctx.get("memory", {}).get("history", [])

        if history:
            ctx["answer"] = f"Summary of {len(history)} conversation turns. (Phase 3: real LLM summarization.)"
        else:
            ctx["answer"] = "No prior conversation to summarize in this session."

        return ctx


summarizer_agent = SummarizerAgent()
