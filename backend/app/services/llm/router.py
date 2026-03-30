"""
LLM Router — selects the correct prompt builder and model for each agent type.

Phase 1: routes to stub builders.
Phase 3: invokes real OpenAI calls via openai_client.
"""

from app.core.logger import get_logger
from app.services.llm import prompts

logger = get_logger(__name__)

AGENT_PROMPT_MAP = {
    "support": prompts.build_support_prompt,
    "research": prompts.build_research_prompt,
    "summarizer": prompts.build_summarizer_prompt,
    "planner": prompts.build_planner_prompt,
}


def get_prompt_builder(agent_name: str):
    """Return the prompt builder function for the given agent."""
    builder = AGENT_PROMPT_MAP.get(agent_name)
    if builder is None:
        logger.warning("llm_router.unknown_agent", extra={"agent": agent_name})
        return prompts.build_support_prompt
    return builder
