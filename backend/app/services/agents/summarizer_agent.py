"""
Summarizer Agent — condenses conversation history or retrieved documents into compact summaries.

Behavior:
- Prioritizes recent message history for conversation summaries
- Falls back to retrieval context when no conversation history exists
- Returns bullet-point condensations for readability
"""

from typing import Any

from app.services.agents.base import BaseAgent, AgentResult

OrchestratorContext = dict[str, Any]


class SummarizerAgent(BaseAgent):
    name = "summarizer"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)

        memory: dict = ctx.get("memory", {})
        recent_messages: list = memory.get("recent_messages", [])
        summary_text: str | None = memory.get("summary_text")
        retrieval_context: str = ctx.get("retrieval_context", "")
        message = ctx["request"].message

        if recent_messages:
            bullets = "\n".join(
                f"- [{m['role'].upper()}]: {m['content'][:120]}{'...' if len(m['content']) > 120 else ''}"
                for m in recent_messages
            )
            prior = f"\n\n**Prior summary on record:** {summary_text}" if summary_text else ""
            answer = (
                f"**Conversation Summary** ({len(recent_messages)} recent message(s)):\n\n"
                f"{bullets}{prior}\n\n"
                "This captures the key exchanges from your recent conversation."
            )
            confidence = 0.9
            reasoning = f"summarized {len(recent_messages)} recent messages"
        elif summary_text:
            answer = (
                f"**Stored Summary:**\n\n{summary_text}\n\n"
                "This is the most recent recorded summary of your conversation history."
            )
            confidence = 0.85
            reasoning = "using stored conversation summary"
        elif retrieval_context:
            # Summarize retrieved documents
            lines = [ln.strip() for ln in retrieval_context.splitlines() if ln.strip()]
            condensed = "\n".join(f"- {ln}" for ln in lines[:8])
            answer = (
                f"**Document Summary** for: \"{message}\"\n\n"
                f"{condensed}\n\n"
                "These are the key points extracted from the relevant documents."
            )
            confidence = 0.8
            reasoning = "summarized retrieval context"
        else:
            answer = (
                "There is no conversation history or indexed content available to summarize.\n\n"
                "To get a summary:\n"
                "- Continue the conversation to build up history, or\n"
                "- Ingest documents via /api/v1/ingest and ask again"
            )
            confidence = 0.3
            reasoning = "no content available to summarize"

        result = self._build_result(
            answer=answer,
            confidence=confidence,
            ctx=ctx,
            reasoning_summary=reasoning,
        )
        ctx["answer"] = answer
        ctx["agent_result"] = result
        return ctx


summarizer_agent = SummarizerAgent()
