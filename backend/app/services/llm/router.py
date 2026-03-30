"""
LLM Router — maps agent names to prompt builders and provides a
unified dispatch helper for agent LLM calls.
"""

from app.core.logger import get_logger
from app.services.llm import prompts

logger = get_logger(__name__)

AGENT_PROMPT_MAP = {
    "support": prompts.build_support_prompt,
    "research": prompts.build_research_prompt,
    "summarizer": prompts.build_summarizer_prompt,
    "planner": prompts.build_planner_prompt,
    "escalation": prompts.build_escalation_prompt,
}


def get_prompt_builder(agent_name: str):
    """Return the prompt builder function for the given agent."""
    builder = AGENT_PROMPT_MAP.get(agent_name)
    if builder is None:
        logger.warning("llm_router.unknown_agent", extra={"agent": agent_name})
        return prompts.build_support_prompt
    return builder


async def call_llm(
    agent_name: str,
    message: str,
    retrieval_context: str = "",
    memory: dict | None = None,
    **extra_kwargs,
) -> str:
    """
    Build the prompt for agent_name and call openai_client.complete().

    Raises on any OpenAI error — callers are responsible for fallback.
    Extra kwargs (e.g. detected_reason) are forwarded to the prompt builder.
    """
    from app.services.llm.openai_client import openai_client

    builder = get_prompt_builder(agent_name)
    messages = builder(
        message=message,
        retrieval_context=retrieval_context,
        memory=memory,
        **extra_kwargs,
    )
    logger.debug(
        "llm_router.call",
        extra={"agent": agent_name, "message_turns": len(messages)},
    )
    return await openai_client.complete(messages=messages)
