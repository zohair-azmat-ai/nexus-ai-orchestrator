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
    tools_used: list[str] = field(default_factory=list)


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
            tools_used=list(ctx.get("tools_used", [])),
        )

    async def _call_tool(
        self,
        ctx: OrchestratorContext,
        tool_name: str,
        **kwargs,
    ) -> dict[str, Any] | None:
        """
        Look up tool_name in the registry, call it, record usage, return result.

        Returns None and logs a warning on any failure so agents can continue.
        The tool name is appended to ctx["tools_used"] on success.
        """
        # Ensure tools package is loaded (registers all tools on first import)
        import app.services.tools  # noqa: F401

        from app.services.tools.registry import tool_registry

        tool = tool_registry.get(tool_name)
        if tool is None:
            self.logger.warning(
                "agent.tool_not_found",
                extra={"tool": tool_name, "agent": self.name},
            )
            return None
        try:
            result = await tool.call(**kwargs)
            ctx.setdefault("tools_used", []).append(tool_name)
            return result
        except Exception as exc:
            self.logger.warning(
                "agent.tool_failed",
                extra={"tool": tool_name, "agent": self.name, "error": str(exc)},
            )
            return None
