from fastapi import APIRouter, HTTPException

from app.core.ids import get_correlation_id
from app.core.logger import get_logger
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import ErrorResponse
from app.services.events import logger as event_logger
from app.services.events.types import EVENT_CHAT_RECEIVED, EVENT_CHAT_COMPLETED, EVENT_CHAT_FAILED
from app.services.orchestrator.engine import run_pipeline

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Chat"],
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Submit a chat message for orchestrated processing.

    The request flows through the full pipeline:
    intake → memory → retrieval → triage → response → escalation → event log
    """
    correlation_id = get_correlation_id()
    logger.info(
        "chat.request",
        extra={
            "correlation_id": correlation_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "message_len": len(request.message),
        },
    )

    event_logger.emit(EVENT_CHAT_RECEIVED, user_id=request.user_id, session_id=request.session_id)

    try:
        response = await run_pipeline(request)
    except Exception as exc:
        logger.error("chat.error", extra={"error": str(exc), "correlation_id": correlation_id})
        event_logger.emit(EVENT_CHAT_FAILED, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    event_logger.emit(
        EVENT_CHAT_COMPLETED,
        agent=response.selected_agent,
        memory_used=response.memory_used,
        retrieval_used=response.retrieval_used,
    )

    return response
