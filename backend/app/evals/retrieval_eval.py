from app.services.retrieval.quality import assess_retrieval_quality
from app.evals.runtime import execute_pipeline_case
from app.evals.types import EvalCaseResult, EvalFailure, RetrievalEvalCase, SuiteReport


async def evaluate_retrieval_case(case: RetrievalEvalCase) -> EvalCaseResult:
    if case.history:
        result = await execute_pipeline_case(
            message=case.input,
            history=case.history,
            retrieval_results=case.retrieval_results,
            user_id=f"retrieval-{case.case_id}",
            session_id=f"retrieval-session-{case.case_id}",
        )
        actual_quality = result.retrieval_quality
        actual_used = result.retrieval_used
        actual_context = result.retrieval_context
        actual_compaction = result.context_compaction_applied
        result_count = result.retrieval_result_count
    else:
        assessment = assess_retrieval_quality(case.retrieval_results)
        actual_quality = assessment.quality
        actual_used = bool(assessment.compacted_results)
        actual_context = assessment.compacted_context
        actual_compaction = assessment.compaction_applied
        result_count = len(assessment.compacted_results)

    failures: list[EvalFailure] = []

    if actual_quality != case.expected_retrieval_quality:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Retrieval quality did not match expected classification.",
                actual={"retrieval_quality": actual_quality},
                expected={"retrieval_quality": case.expected_retrieval_quality},
            )
        )

    if actual_used != case.expected_retrieval_used:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Retrieval usage flag did not match expectation.",
                actual={"retrieval_used": actual_used},
                expected={"retrieval_used": case.expected_retrieval_used},
            )
        )

    if case.expect_compaction != actual_compaction:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Context compaction flag did not match expectation.",
                actual={"context_compaction_applied": actual_compaction},
                expected={"context_compaction_applied": case.expect_compaction},
            )
        )

    retrieval_context = actual_context.lower()
    missing_sources = [
        source for source in case.expected_sources if source.lower() not in retrieval_context
    ]
    if missing_sources:
        failures.append(
            EvalFailure(
                case_id=case.case_id,
                message="Expected retrieval sources were missing from the compacted context.",
                actual={"retrieval_context": actual_context},
                expected={"sources_present": case.expected_sources},
            )
        )

    return EvalCaseResult(
        case_id=case.case_id,
        passed=not failures,
        details={
            "retrieval_quality": actual_quality,
            "retrieval_used": actual_used,
            "retrieval_result_count": result_count,
            "context_compaction_applied": actual_compaction,
        },
        failures=failures,
    )


async def run_retrieval_eval(cases: list[RetrievalEvalCase]) -> SuiteReport:
    case_results = [await evaluate_retrieval_case(case) for case in cases]
    return SuiteReport.from_case_results("retrieval", case_results)
