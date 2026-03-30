from fastapi import APIRouter

from app.core.logger import get_logger
from app.schemas.memory import MemoryResponse
from app.services.memory.manager import memory_manager

router = APIRouter()
logger = get_logger(__name__)


@router.get("/memory/{user_id}", response_model=MemoryResponse, tags=["Memory"])
async def get_user_memory(user_id: str) -> MemoryResponse:
    """
    Retrieve memory context for a given user.

    Returns short-term conversation history and long-term summary.
    Phase 1: in-process memory only (resets on restart).
    Phase 2: backed by PostgreSQL.
    """
    logger.info("memory.get", extra={"user_id": user_id})
    return await memory_manager.get_user_summary(user_id)
