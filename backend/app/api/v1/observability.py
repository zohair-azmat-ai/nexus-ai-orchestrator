from fastapi import APIRouter

from app.core.config import settings
from app.services.analytics.aggregator import get_all

router = APIRouter()


@router.get("/observability/health", tags=["Observability"])
async def observability_health() -> dict:
    """
    Lightweight observability status endpoint.

    Returns current in-memory metric counters and service info.
    Phase 5: integrate with Prometheus / OpenTelemetry exporter.
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "metrics": get_all(),
    }
