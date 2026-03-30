from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.services.analytics.aggregator import get_all, get_metrics_snapshot
from app.services.observability.store import get_trace_summary

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


@router.get("/observability/metrics", tags=["Observability"])
async def observability_metrics() -> dict:
    """Return lightweight in-memory metrics for requests, agents, tools, jobs, and errors."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "metrics": get_metrics_snapshot(),
    }


@router.get("/observability/trace/{trace_id}", tags=["Observability"])
async def observability_trace(trace_id: str) -> dict:
    """Return all in-memory events collected for a specific trace."""
    summary = get_trace_summary(trace_id)
    if not summary["events"]:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id!r} not found")
    return summary
