"""
SummarizeConversation tool — wraps the memory summarizer service.

Agents can call this to generate a fresh summary from a list of messages,
independent of what the memory stage may have already stored.
"""

from typing import Any

from app.services.tools.base_tool import BaseTool


class SummarizeConversationTool(BaseTool):
    name = "summarize_conversation"
    description = (
        "Generates a concise summary from a list of conversation messages. "
        "Uses LLM summarization when available, deterministic fallback otherwise."
    )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "messages": "list[dict] — list of {role, content} message dicts to summarize",
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        from app.services.memory.summarizer import conversation_summarizer

        messages: list[dict] = kwargs["messages"]
        summary = await conversation_summarizer.summarize(messages)

        return {
            "summary": summary,
            "source_count": len(messages),
        }


summarize_conversation_tool = SummarizeConversationTool()
