import pytest

from app.evals.agent_eval import evaluate_agent_case
from app.evals.datasets import (
    load_agent_cases,
    load_memory_cases,
    load_regression_cases,
    load_retrieval_cases,
)
from app.evals.memory_eval import evaluate_memory_case
from app.evals.reporting import build_combined_report, save_report
from app.evals.regression_eval import evaluate_regression_case
from app.evals.retrieval_eval import evaluate_retrieval_case
from app.evals.runner import run_eval_suite


def test_eval_datasets_load_successfully():
    retrieval_cases = load_retrieval_cases()
    memory_cases = load_memory_cases()
    agent_cases = load_agent_cases()
    regression_cases = load_regression_cases()

    assert len(retrieval_cases) >= 4
    assert len(memory_cases) >= 4
    assert len(agent_cases) >= 5
    assert len(regression_cases) >= 5


@pytest.mark.asyncio
async def test_retrieval_eval_case_passes_for_strong_dataset_case():
    case = next(item for item in load_retrieval_cases() if item.case_id == "retrieval-strong-docs")
    result = await evaluate_retrieval_case(case)

    assert result.passed is True
    assert result.details["retrieval_quality"] == "strong"


def test_memory_eval_case_passes_for_stale_dataset_case():
    case = next(item for item in load_memory_cases() if item.case_id == "memory-stale-high-signal")
    result = evaluate_memory_case(case)

    assert result.passed is True
    assert result.details["memory_freshness"] == "stale"


@pytest.mark.asyncio
async def test_agent_eval_case_passes_for_planner_multistep_case():
    case = next(item for item in load_agent_cases() if item.case_id == "agent-planner-multistep")
    result = await evaluate_agent_case(case)

    assert result.passed is True
    assert result.details["execution_mode"] == "multi_step"


@pytest.mark.asyncio
async def test_regression_eval_case_passes_for_memory_followup():
    case = next(item for item in load_regression_cases() if item.case_id == "regression-memory-followup")
    result = await evaluate_regression_case(case)

    assert result.passed is True
    assert result.details["memory_used"] is True
    assert result.details["retrieval_used"] is False


@pytest.mark.asyncio
async def test_eval_runner_and_report_generation():
    payload = await run_eval_suite("all")
    report_path = save_report(payload, "eval_reports/test-eval-report.json")

    combined = build_combined_report([])
    assert payload["suite_name"] == "all"
    assert payload["total_cases"] >= 1
    assert report_path.exists()
    assert combined["suite_name"] == "all"
    report_path.unlink(missing_ok=True)
