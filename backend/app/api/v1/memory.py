from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.db.postgres import get_db
from app.schemas.memory import MemoryResponse
from app.services.memory.manager import memory_manager

router = APIRouter()
logger = get_logger(__name__)


@router.get("/memory/{user_id}", response_model=MemoryResponse, tags=["Memory"])
async def get_user_memory(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> MemoryResponse:
    """
    Retrieve memory context for a given user.

    Returns recent conversation messages and latest LLM-generated summary.
    """
    logger.info("memory.get", extra={"user_id": user_id})
    return await memory_manager.get_user_summary(db, user_id)
