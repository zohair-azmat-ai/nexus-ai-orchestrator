from app.services.memory.freshness import assess_memory_freshness, select_recent_messages
from app.evals.types import EvalCaseResult, EvalFailure, MemoryEvalCase, SuiteReport


def evaluate_memory_case(case: MemoryEvalCase) -> EvalCaseResult:
    selected_recent_messages, compacted = select_recent_messages(
        case.recent_messages,
        limit=case.selection_limit,
    )
    assessment = assess_memory_freshness(
        summary_text=case.summary_text,
        summary_version=case.summary_version,
        source_message_count=case.source_message_count,
        total_message_count=case.total_message_count,
        recent_messages=case.recent_messages,
        selected_recent_messages=selected_recent_messages,
    )

    failures: list[EvalFailure] = []

    if assessment.freshness != case.expected_memory_freshness:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Memory freshness classification did not match expectation.",
                actual={"memory_freshness": assessment.freshness},
                expected={"memory_freshness": case.expected_memory_freshness},
            )
        )

    if assessment.refresh_recommended != case.expected_refresh_recommended:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Summary refresh recommendation did not match expectation.",
                actual={"summary_refresh_recommended": assessment.refresh_recommended},
                expected={"summary_refresh_recommended": case.expected_refresh_recommended},
            )
        )

    if len(selected_recent_messages) != case.expected_selected_count:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Selected recent-message count did not match expectation.",
                actual={"selected_count": len(selected_recent_messages)},
                expected={"selected_count": case.expected_selected_count},
            )
        )

    if bool(selected_recent_messages) != case.expected_memory_usage:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Memory usage expectation did not match selected-message output.",
                actual={"memory_used": bool(selected_recent_messages)},
                expected={"memory_used": case.expected_memory_usage},
            )
        )

    if compacted != case.expect_compaction:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Recent-message compaction flag did not match expectation.",
                actual={"context_compaction_applied": compacted},
                expected={"context_compaction_applied": case.expect_compaction},
            )
        )

    return EvalCaseResult(
        case_id=case.case_id,
        passed=not failures,
        details={
            "memory_freshness": assessment.freshness,
            "summary_refresh_recommended": assessment.refresh_recommended,
            "selected_count": len(selected_recent_messages),
            "context_compaction_applied": compacted,
        },
        failures=failures,
    )


async def run_memory_eval(cases: list[MemoryEvalCase]) -> SuiteReport:
    case_results = [evaluate_memory_case(case) for case in cases]
    return SuiteReport.from_case_results("memory", case_results)
