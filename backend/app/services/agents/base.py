"""
Base Agent — all agents inherit from this class.

An agent receives an OrchestratorContext, processes the request using
its specialization, and returns an updated context with both
`answer` and `agent_result` populated.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.logger import get_logger

OrchestratorContext = dict[str, Any]


@dataclass
class AgentResult:
    """Structured result returned by every agent execution."""
    agent_name: str
    answer: str
    confidence: float                      # 0.0 – 1.0
    used_memory: bool
    used_retrieval: bool
    escalation_required: bool
    reasoning_summary: str = ""
    notes: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self) -> None:
        self.logger = get_logger(f"agent.{self.name}")

    @abstractmethod
    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        """
        Execute agent logic, populate ctx["answer"] and ctx["agent_result"].

        Args:
            ctx: shared orchestrator context dict

        Returns:
            Updated context dict.
        """

    def _log_run(self, ctx: OrchestratorContext) -> None:
        self.logger.info(
            "agent.run",
            extra={
                "agent": self.name,
                "user_id": ctx["request"].user_id,
                "correlation_id": ctx.get("correlation_id", ""),
            },
        )

    def _build_result(
        self,
        answer: str,
        confidence: float,
        ctx: OrchestratorContext,
        escalation_required: bool = False,
        reasoning_summary: str = "",
        notes: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Helper to construct an AgentResult from current context."""
        return AgentResult(
            agent_name=self.name,
            answer=answer,
            confidence=confidence,
            used_memory=ctx.get("memory_used", False),
            used_retrieval=ctx.get("retrieval_used", False),
            escalation_required=escalation_required,
            reasoning_summary=reasoning_summary,
            notes=notes or {},
        )
