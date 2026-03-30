"""
Base Agent — all agents inherit from this class.

An agent receives an OrchestratorContext, processes the request using
its specialization, and returns an updated context with `answer` populated.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.core.logger import get_logger

OrchestratorContext = dict[str, Any]


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self) -> None:
        self.logger = get_logger(f"agent.{self.name}")

    @abstractmethod
    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        """
        Execute agent logic and populate ctx["answer"].

        Args:
            ctx: shared orchestrator context dict

        Returns:
            Updated context dict with answer field set.
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
