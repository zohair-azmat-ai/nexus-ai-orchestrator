"""
Lightweight execution-plan models for deterministic orchestration.
"""

from dataclasses import dataclass, field
from typing import Any

from app.core.ids import generate_id


@dataclass
class ExecutionStep:
    step_id: str
    type: str
    target: str
    purpose: str
    status: str = "pending"
    input_summary: str = ""
    output_summary: str = ""
    recommended_tools: list[str] = field(default_factory=list)
    required_context: list[str] = field(default_factory=list)
    can_skip: bool = False
    skip_reason: str | None = None
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "type": self.type,
            "target": self.target,
            "purpose": self.purpose,
            "status": self.status,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "recommended_tools": list(self.recommended_tools),
            "required_context": list(self.required_context),
            "can_skip": self.can_skip,
            "skip_reason": self.skip_reason,
            "depends_on": list(self.depends_on),
        }


@dataclass
class ExecutionPlan:
    plan_id: str
    steps: list[ExecutionStep] = field(default_factory=list)

    @property
    def execution_mode(self) -> str:
        runnable = [step for step in self.steps if step.type in {"agent", "system", "tool"}]
        return "multi_step" if len(runnable) > 1 else "single_step"

    @property
    def tools_planned(self) -> list[str]:
        seen: list[str] = []
        for step in self.steps:
            for tool in step.recommended_tools:
                if tool not in seen:
                    seen.append(tool)
        return seen

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "execution_mode": self.execution_mode,
            "tools_planned": self.tools_planned,
            "steps": [step.to_dict() for step in self.steps],
        }


def make_agent_step(
    target: str,
    purpose: str,
    *,
    recommended_tools: list[str] | None = None,
    required_context: list[str] | None = None,
    can_skip: bool = False,
    skip_reason: str | None = None,
    depends_on: list[str] | None = None,
) -> ExecutionStep:
    return ExecutionStep(
        step_id=generate_id(),
        type="agent",
        target=target,
        purpose=purpose,
        recommended_tools=recommended_tools or [],
        required_context=required_context or [],
        can_skip=can_skip,
        skip_reason=skip_reason,
        depends_on=depends_on or [],
    )


def make_system_step(
    target: str,
    purpose: str,
    *,
    required_context: list[str] | None = None,
    depends_on: list[str] | None = None,
) -> ExecutionStep:
    return ExecutionStep(
        step_id=generate_id(),
        type="system",
        target=target,
        purpose=purpose,
        required_context=required_context or [],
        depends_on=depends_on or [],
    )


def make_plan(steps: list[ExecutionStep]) -> ExecutionPlan:
    return ExecutionPlan(plan_id=generate_id(), steps=steps)
