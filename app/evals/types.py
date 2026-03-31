from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal


SuiteName = Literal["retrieval", "memory", "agent", "regression"]


@dataclass
class RetrievalEvalCase:
    case_id: str
    category: str
    input: str
    retrieval_results: list[dict[str, Any]]
    history: list[dict[str, str]] = field(default_factory=list)
    expected_behavior: str = ""
    expected_retrieval_quality: str = "none"
    expected_retrieval_used: bool = False
    expected_sources: list[str] = field(default_factory=list)
    expect_compaction: bool = False
    notes: str = ""


@dataclass
class MemoryEvalCase:
    case_id: str
    category: str
    input: str
    summary_text: str | None
    summary_version: int
    source_message_count: int
    total_message_count: int
    recent_messages: list[dict[str, str]]
    selection_limit: int
    expected_behavior: str = ""
    expected_memory_freshness: str = "empty"
    expected_refresh_recommended: bool = False
    expected_selected_count: int = 0
    expected_memory_usage: bool = False
    expect_compaction: bool = False
    notes: str = ""


@dataclass
class AgentEvalCase:
    case_id: str
    category: str
    input: str
    history: list[dict[str, str]] = field(default_factory=list)
    retrieval_results: list[dict[str, Any]] = field(default_factory=list)
    expected_behavior: str = ""
    expected_agent: str = "support"
    expected_execution_mode: str = "single_step"
    expected_escalated: bool = False
    expected_tools_planned: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class RegressionEvalCase:
    case_id: str
    category: str
    input: str
    history: list[dict[str, str]] = field(default_factory=list)
    retrieval_results: list[dict[str, Any]] = field(default_factory=list)
    expected_behavior: str = ""
    expected_agent: str = "support"
    expected_execution_mode: str = "single_step"
    expected_retrieval_quality: str = "none"
    expected_memory_freshness: str = "empty"
    expected_escalated: bool = False
    expected_memory_used: bool = False
    expected_retrieval_used: bool = False
    expected_response_fields: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class EvalFailure:
    case_id: str
    message: str
    actual: dict[str, Any] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalCaseResult:
    case_id: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    failures: list[EvalFailure] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "details": self.details,
            "failures": [asdict(failure) for failure in self.failures],
        }


@dataclass
class SuiteReport:
    suite_name: SuiteName
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    failures: list[dict[str, Any]]
    case_results: list[dict[str, Any]]
    generated_at: str

    @classmethod
    def from_case_results(cls, suite_name: SuiteName, case_results: list[EvalCaseResult]) -> "SuiteReport":
        failures = [
            {"case_id": result.case_id, "failures": [asdict(item) for item in result.failures]}
            for result in case_results
            if not result.passed
        ]
        passed_cases = sum(1 for result in case_results if result.passed)
        total_cases = len(case_results)
        failed_cases = total_cases - passed_cases
        pass_rate = round((passed_cases / total_cases) * 100, 2) if total_cases else 0.0
        return cls(
            suite_name=suite_name,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            pass_rate=pass_rate,
            failures=failures,
            case_results=[result.to_dict() for result in case_results],
            generated_at=datetime.utcnow().isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
