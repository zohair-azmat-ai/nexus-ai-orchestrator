import json
from pathlib import Path
from typing import Any

from app.evals.types import SuiteName, SuiteReport

EVAL_REPORTS_DIR = Path(__file__).resolve().parents[2] / "eval_reports"


def build_combined_report(suite_reports: list[SuiteReport]) -> dict[str, Any]:
    total_cases = sum(report.total_cases for report in suite_reports)
    passed_cases = sum(report.passed_cases for report in suite_reports)
    failed_cases = sum(report.failed_cases for report in suite_reports)
    pass_rate = round((passed_cases / total_cases) * 100, 2) if total_cases else 0.0

    return {
        "suite_name": "all",
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "pass_rate": pass_rate,
        "generated_at": suite_reports[0].generated_at if suite_reports else "",
        "suites": [report.to_dict() for report in suite_reports],
    }


def save_report(payload: dict[str, Any], report_path: str | None = None) -> Path:
    if report_path:
        path = Path(report_path)
    else:
        EVAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        suite_name = payload.get("suite_name", "eval")
        generated_at = str(payload.get("generated_at", "report")).replace(":", "-")
        path = EVAL_REPORTS_DIR / f"{suite_name}-{generated_at}.json"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
