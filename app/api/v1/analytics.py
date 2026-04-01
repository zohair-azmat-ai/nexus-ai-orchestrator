from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.postgres import get_db
from app.schemas.analytics import AnalyticsSummaryResponse

router = APIRouter()


@router.get(
    "/analytics/summary",
    response_model=AnalyticsSummaryResponse,
    tags=["Analytics"],
)
async def analytics_summary(db: AsyncSession = Depends(get_db)) -> AnalyticsSummaryResponse:
    summary = await crud.get_analytics_summary(db)
    return AnalyticsSummaryResponse(**summary)
