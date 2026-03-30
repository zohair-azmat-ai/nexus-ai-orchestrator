"""
Lightweight execution-plan models for deterministic multi-step orchestration.
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "type": self.type,
            "target": self.target,
            "purpose": self.purpose,
            "status": self.status,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
        }


@dataclass
class ExecutionPlan:
    plan_id: str
    steps: list[ExecutionStep] = field(default_factory=list)

    @property
    def execution_mode(self) -> str:
        return "multi_step" if len(self.steps) > 1 else "single_step"

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "execution_mode": self.execution_mode,
            "steps": [step.to_dict() for step in self.steps],
        }


def make_agent_step(target: str, purpose: str) -> ExecutionStep:
    return ExecutionStep(
        step_id=generate_id(),
        type="agent",
        target=target,
        purpose=purpose,
    )


def make_plan(steps: list[ExecutionStep]) -> ExecutionPlan:
    return ExecutionPlan(plan_id=generate_id(), steps=steps)
