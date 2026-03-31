from app.evals.runtime import execute_pipeline_case
from app.evals.types import EvalCaseResult, EvalFailure, RegressionEvalCase, SuiteReport


async def evaluate_regression_case(case: RegressionEvalCase) -> EvalCaseResult:
    result = await execute_pipeline_case(
        message=case.input,
        history=case.history,
        retrieval_results=case.retrieval_results,
        user_id=f"regression-{case.case_id}",
        session_id=f"regression-session-{case.case_id}",
    )

    failures: list[EvalFailure] = []

    def expect_equal(field: str, actual_value, expected_value) -> None:
        if actual_value != expected_value:
            failures.append(
                EvalFailure(
                    case_id=case.case_id,
                    message=f"{field} did not match expectation.",
                    actual={field: actual_value},
                    expected={field: expected_value},
                )
            )

    expect_equal("selected_agent", result.selected_agent, case.expected_agent)
    expect_equal("execution_mode", result.execution_mode, case.expected_execution_mode)
    expect_equal("retrieval_quality", result.retrieval_quality, case.expected_retrieval_quality)
    expect_equal("memory_freshness", result.memory_freshness, case.expected_memory_freshness)
    expect_equal("memory_used", result.memory_used, case.expected_memory_used)
    expect_equal("retrieval_used", result.retrieval_used, case.expected_retrieval_used)
    expect_equal("escalated", result.event_summary.get("escalated", False), case.expected_escalated)

    result_payload = result.__dict__
    missing_fields = [field for field in case.expected_response_fields if field not in result_payload]
    if missing_fields:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Response metadata shape regressed.",
                actual={"available_fields": sorted(result_payload.keys())},
                expected={"required_fields": case.expected_response_fields},
            )
        )

    return EvalCaseResult(
        case_id=case.case_id,
        passed=not failures,
        details={
            "selected_agent": result.selected_agent,
            "execution_mode": result.execution_mode,
            "retrieval_quality": result.retrieval_quality,
            "memory_freshness": result.memory_freshness,
            "memory_used": result.memory_used,
            "retrieval_used": result.retrieval_used,
            "escalated": result.event_summary.get("escalated", False),
        },
        failures=failures,
    )


async def run_regression_eval(cases: list[RegressionEvalCase]) -> SuiteReport:
    case_results = [await evaluate_regression_case(case) for case in cases]
    return SuiteReport.from_case_results("regression", case_results)
