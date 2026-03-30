from datetime import datetime

from fastapi import APIRouter

from app.core.config import settings
from app.core.logger import get_logger
from app.db.postgres import check_postgres_connection
from app.db.qdrant import check_qdrant_connection
from app.schemas.common import HealthResponse

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    System health check.

    Returns service status, version, environment, and dependency availability.
    """
    postgres_ok = await check_postgres_connection()
    qdrant_ok = await check_qdrant_connection()

    status = "ok" if (postgres_ok and qdrant_ok) else "degraded"

    logger.info("health.check", extra={"status": status, "postgres": postgres_ok, "qdrant": qdrant_ok})

    return HealthResponse(
        status=status,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        postgres=postgres_ok,
        qdrant=qdrant_ok,
        timestamp=datetime.utcnow(),
    )
