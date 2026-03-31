from datetime import datetime

from fastapi import APIRouter

from app.core.config import settings
from app.core.logger import get_logger
from app.db.postgres import check_postgres_connection
from app.db.qdrant import check_qdrant_connection
from app.schemas.common import DependencyStatus, HealthResponse, ReadinessResponse

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Lightweight liveness endpoint for process-level health.
    """
    status = "ok"
    logger.info("health.liveness", extra={"status": status})

    return HealthResponse(
        status=status,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.utcnow(),
    )


@router.get("/ready", response_model=ReadinessResponse, tags=["Health"])
async def readiness_check() -> ReadinessResponse:
    """
    Readiness endpoint that validates critical dependencies before serving traffic.
    """
    postgres_ok = await check_postgres_connection()
    qdrant_ok = await check_qdrant_connection()

    dependencies = {
        "database": DependencyStatus(
            status="ok" if postgres_ok else "unavailable",
            available=postgres_ok,
            checked_at=datetime.utcnow(),
        ),
        "qdrant": DependencyStatus(
            status="ok" if qdrant_ok else "unavailable",
            available=qdrant_ok,
            checked_at=datetime.utcnow(),
        ),
    }
    status = "ready" if all(item.available for item in dependencies.values()) else "degraded"

    logger.info(
        "health.readiness",
        extra={
            "status": status,
            "database": dependencies["database"].available,
            "qdrant": dependencies["qdrant"].available,
        },
    )

    return ReadinessResponse(
        status=status,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        dependencies=dependencies,
        timestamp=datetime.utcnow(),
    )
