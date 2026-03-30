"""
Conversation Summarizer — condenses long history into a compact summary.

Uses OpenAI when the API key is available and LLM summarization is enabled.
Falls back to a deterministic local summary when OpenAI is unavailable.
"""

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are a concise conversation summarizer. "
    "Given a list of chat messages, produce a single-paragraph summary "
    "capturing the key topics, decisions, and unresolved questions. "
    "Keep it under 200 words."
)


class ConversationSummarizer:
    async def summarize(self, history: list[dict]) -> str:
        """
        Summarize a list of message turns.

        Args:
            history: list of {"role": str, "content": str} dicts

        Returns:
            A string summary (LLM-generated or deterministic fallback).
        """
        if not history:
            return ""

        if settings.memory_enable_llm_summarization and settings.openai_api_key:
            try:
                return await self._llm_summarize(history)
            except Exception as exc:
                logger.warning(
                    "summarizer.llm_failed",
                    extra={"error": str(exc), "turns": len(history)},
                )

        return self._deterministic_summarize(history)

    async def _llm_summarize(self, history: list[dict]) -> str:
        from app.services.llm.openai_client import openai_client

        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
        for turn in history:
            messages.append({"role": turn["role"], "content": turn["content"]})

        response = await openai_client.complete(messages=messages)
        logger.info("summarizer.llm_done", extra={"turns": len(history)})
        return response

    def _deterministic_summarize(self, history: list[dict]) -> str:
        """Build a brief fallback summary without calling any external service."""
        user_msgs = [t["content"] for t in history if t.get("role") == "user"]
        if not user_msgs:
            return f"Conversation with {len(history)} turns."

        topics = "; ".join(user_msgs[:3])
        suffix = f" (and {len(user_msgs) - 3} more)" if len(user_msgs) > 3 else ""
        return f"User discussed: {topics}{suffix}. ({len(history)} total turns)"


conversation_summarizer = ConversationSummarizer()
