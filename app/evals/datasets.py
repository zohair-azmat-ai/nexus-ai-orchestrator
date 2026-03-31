import json
from pathlib import Path
from typing import TypeVar

from app.evals.types import AgentEvalCase, MemoryEvalCase, RegressionEvalCase, RetrievalEvalCase

DatasetT = TypeVar("DatasetT", RetrievalEvalCase, MemoryEvalCase, AgentEvalCase, RegressionEvalCase)

EVALS_DATA_DIR = Path(__file__).resolve().parents[2] / "evals_data"


def _load_cases(file_name: str, case_type: type[DatasetT]) -> list[DatasetT]:
    path = EVALS_DATA_DIR / file_name
    with path.open("r", encoding="utf-8") as handle:
        raw_cases = json.load(handle)
    return [case_type(**case) for case in raw_cases]


def load_retrieval_cases() -> list[RetrievalEvalCase]:
    return _load_cases("retrieval_cases.json", RetrievalEvalCase)


def load_memory_cases() -> list[MemoryEvalCase]:
    return _load_cases("memory_cases.json", MemoryEvalCase)


def load_agent_cases() -> list[AgentEvalCase]:
    return _load_cases("agent_cases.json", AgentEvalCase)


def load_regression_cases() -> list[RegressionEvalCase]:
    return _load_cases("regression_cases.json", RegressionEvalCase)
