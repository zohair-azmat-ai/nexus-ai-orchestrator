"""
Support Agent — handles general customer support, troubleshooting, and help queries.

Behavior:
- Grounded, direct answer referencing retrieval context when available
- Acknowledges memory/conversation history when present
- Confidence reflects evidence quality
"""

from typing import Any

from app.services.agents.base import BaseAgent, AgentResult

OrchestratorContext = dict[str, Any]


class SupportAgent(BaseAgent):
    name = "support"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)

        message = ctx["request"].message
        retrieval_context: str = ctx.get("retrieval_context", "")
        memory: dict = ctx.get("memory", {})
        summary_text: str | None = memory.get("summary_text")
        recent_messages: list = memory.get("recent_messages", [])

        if retrieval_context:
            answer = (
                "Based on our knowledge base, here is what I found:\n\n"
                f"{retrieval_context}\n\n"
                "If this doesn't fully address your issue, please share more details "
                "and I'll investigate further."
            )
            confidence = 0.9
            reasoning = "retrieval context available"
        elif summary_text:
            answer = (
                f"Based on our conversation history: {summary_text}\n\n"
                f"Regarding your question — \"{message}\" — "
                "I recommend reviewing the relevant documentation or contacting "
                "our support team directly if the issue persists."
            )
            confidence = 0.7
            reasoning = "memory summary available"
        elif recent_messages:
            turns = len(recent_messages)
            answer = (
                f"I can see we've been talking for {turns} message(s). "
                f"Regarding \"{message}\": I'm here to help — could you provide "
                "more details about what you're experiencing so I can assist better?"
            )
            confidence = 0.65
            reasoning = "recent message history available"
        else:
            answer = (
                f"I'm here to help with: \"{message}\".\n\n"
                "To give you the most accurate support, please describe:\n"
                "1. What you were trying to do\n"
                "2. What happened instead\n"
                "3. Any error messages you saw"
            )
            confidence = 0.5
            reasoning = "no retrieval or memory context"

        result = self._build_result(
            answer=answer,
            confidence=confidence,
            ctx=ctx,
            reasoning_summary=reasoning,
        )
        ctx["answer"] = answer
        ctx["agent_result"] = result
        return ctx


support_agent = SupportAgent()
