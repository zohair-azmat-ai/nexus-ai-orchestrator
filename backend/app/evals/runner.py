import argparse
import asyncio
from typing import Any

from app.evals.agent_eval import run_agent_eval
from app.evals.datasets import (
    load_agent_cases,
    load_memory_cases,
    load_regression_cases,
    load_retrieval_cases,
)
from app.evals.memory_eval import run_memory_eval
from app.evals.regression_eval import run_regression_eval
from app.evals.reporting import build_combined_report, save_report
from app.evals.retrieval_eval import run_retrieval_eval
from app.evals.types import SuiteName, SuiteReport

SUITES: dict[SuiteName, Any] = {
    "retrieval": lambda: run_retrieval_eval(load_retrieval_cases()),
    "memory": lambda: run_memory_eval(load_memory_cases()),
    "agent": lambda: run_agent_eval(load_agent_cases()),
    "regression": lambda: run_regression_eval(load_regression_cases()),
}


async def run_eval_suite(
    suite_name: str = "all",
    report_path: str | None = None,
    save_json: bool = False,
) -> dict[str, Any]:
    if suite_name == "all":
        suite_reports: list[SuiteReport] = []
        for name, runner in SUITES.items():
            suite_reports.append(await runner())
        payload = build_combined_report(suite_reports)
    else:
        runner = SUITES[suite_name]  # type: ignore[index]
        suite_report = await runner()
        payload = suite_report.to_dict()

    if save_json or report_path is not None:
        saved_path = save_report(payload, report_path)
        payload["report_path"] = str(saved_path)

    return payload


def _print_summary(payload: dict[str, Any]) -> None:
    print(f"Suite: {payload['suite_name']}")
    print(f"Total cases: {payload['total_cases']}")
    print(f"Passed: {payload['passed_cases']}")
    print(f"Failed: {payload['failed_cases']}")
    print(f"Pass rate: {payload['pass_rate']}%")

    if payload["suite_name"] == "all":
        for suite in payload.get("suites", []):
            print(
                f"- {suite['suite_name']}: {suite['passed_cases']}/{suite['total_cases']} passed"
            )

    failing_case_ids: list[str] = []
    if payload["suite_name"] == "all":
        for suite in payload.get("suites", []):
            failing_case_ids.extend(item["case_id"] for item in suite.get("failures", []))
    else:
        failing_case_ids.extend(item["case_id"] for item in payload.get("failures", []))

    if failing_case_ids:
        print(f"Failing case IDs: {', '.join(failing_case_ids)}")

    if payload.get("report_path"):
        print(f"Report saved to: {payload['report_path']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Nexus AI evaluation suites.")
    parser.add_argument(
        "--suite",
        choices=["all", *SUITES.keys()],
        default="all",
        help="Run a single suite or all suites.",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Optional path to save the JSON report. Defaults to backend/eval_reports/ when omitted with --save-report.",
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Persist the JSON report under backend/eval_reports/ or the provided --report-path.",
    )
    args = parser.parse_args()

    payload = asyncio.run(
        run_eval_suite(args.suite, report_path=args.report_path, save_json=args.save_report)
    )
    _print_summary(payload)


if __name__ == "__main__":
    main()
