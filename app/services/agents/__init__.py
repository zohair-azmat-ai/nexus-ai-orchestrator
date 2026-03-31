"""
Agent registry — maps agent names to their singleton instances.

Import from here to look up an agent by name at runtime.
"""

from app.services.agents.support_agent import support_agent
from app.services.agents.research_agent import research_agent
from app.services.agents.summarizer_agent import summarizer_agent
from app.services.agents.planner_agent import planner_agent
from app.services.agents.escalation_agent import escalation_agent
from app.services.agents.base import BaseAgent, AgentResult

AGENT_REGISTRY: dict[str, BaseAgent] = {
    "support": support_agent,
    "research": research_agent,
    "summarizer": summarizer_agent,
    "planner": planner_agent,
    "escalation": escalation_agent,
}

__all__ = [
    "AGENT_REGISTRY",
    "BaseAgent",
    "AgentResult",
    "support_agent",
    "research_agent",
    "summarizer_agent",
    "planner_agent",
    "escalation_agent",
]
