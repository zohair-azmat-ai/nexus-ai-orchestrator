from unittest.mock import AsyncMock, patch

from app.core.ids import generate_id, set_correlation_id, set_trace_id
from app.schemas.chat import ChatMessage, ChatRequest
from app.schemas.pipeline import PipelineResult
from app.services.orchestrator.engine import run_pipeline


async def execute_pipeline_case(
    *,
    message: str,
    history: list[dict[str, str]] | None = None,
    retrieval_results: list[dict] | None = None,
    user_id: str = "eval-user",
    session_id: str = "eval-session",
) -> PipelineResult:
    trace_id = generate_id()
    set_correlation_id(trace_id)
    set_trace_id(trace_id)

    request = ChatRequest(
        user_id=user_id,
        session_id=session_id,
        message=message,
        history=[ChatMessage(**item) for item in (history or [])],
        metadata={"eval": True},
    )

    mocked_results = retrieval_results if retrieval_results is not None else []
    with (
        patch("app.core.config.settings.openai_api_key", ""),
        patch(
            "app.services.retrieval.search.semantic_search.search",
            new=AsyncMock(return_value=mocked_results),
        ),
    ):
        return await run_pipeline(request)
