from app.evals.runtime import execute_pipeline_case
from app.evals.types import AgentEvalCase, EvalCaseResult, EvalFailure, SuiteReport


async def evaluate_agent_case(case: AgentEvalCase) -> EvalCaseResult:
    result = await execute_pipeline_case(
        message=case.input,
        history=case.history,
        retrieval_results=case.retrieval_results,
        user_id=f"agent-{case.case_id}",
        session_id=f"agent-session-{case.case_id}",
    )

    failures: list[EvalFailure] = []

    if result.selected_agent != case.expected_agent:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Selected agent did not match expectation.",
                actual={"selected_agent": result.selected_agent},
                expected={"selected_agent": case.expected_agent},
            )
        )

    if result.execution_mode != case.expected_execution_mode:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Execution mode did not match expectation.",
                actual={"execution_mode": result.execution_mode},
                expected={"execution_mode": case.expected_execution_mode},
            )
        )

    if result.event_summary.get("escalated", False) != case.expected_escalated:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Escalation flag did not match expectation.",
                actual={"escalated": result.event_summary.get("escalated", False)},
                expected={"escalated": case.expected_escalated},
            )
        )

    missing_tools = [tool for tool in case.expected_tools_planned if tool not in result.tools_planned]
    if missing_tools:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Expected planned tools were missing.",
                actual={"tools_planned": result.tools_planned},
                expected={"tools_planned_contains": case.expected_tools_planned},
            )
        )

    return EvalCaseResult(
        case_id=case.case_id,
        passed=not failures,
        details={
            "selected_agent": result.selected_agent,
            "execution_mode": result.execution_mode,
            "tools_planned": result.tools_planned,
            "escalated": result.event_summary.get("escalated", False),
        },
        failures=failures,
    )


async def run_agent_eval(cases: list[AgentEvalCase]) -> SuiteReport:
    case_results = [await evaluate_agent_case(case) for case in cases]
    return SuiteReport.from_case_results("agent", case_results)
