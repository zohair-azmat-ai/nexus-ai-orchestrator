from contextlib import asynccontextmanager
from pathlib import Path
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import public
from app.api.v1 import analytics, auth, chat, escalations, health, ingest, jobs, memory, observability
from app.core.config import settings
from app.core.ids import generate_id, set_correlation_id, set_trace_id
from app.core.logger import clear_log_context, get_logger, set_log_context
from app.db.postgres import create_all_tables, get_db
from app.services.analytics.aggregator import record_request
from app.services.auth import auth_manager
from app.services.events import logger as event_logger
from app.services.events.types import (
    EVENT_API_REQUEST_COMPLETED,
    EVENT_API_REQUEST_FAILED,
    EVENT_API_REQUEST_STARTED,
    EVENT_SHUTDOWN,
    EVENT_STARTUP,
)

logger = get_logger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_errors = settings.validate_runtime_configuration()
    if config_errors:
        logger.error("nexus.config.invalid", extra={"errors": config_errors})
        message = "Invalid runtime configuration:\n- " + "\n- ".join(config_errors)
        raise RuntimeError(message)

    logger.info(
        "nexus.startup",
        extra={"service": settings.app_name, "version": settings.app_version, "env": settings.app_env},
    )
    event_logger.emit(EVENT_STARTUP, service=settings.app_name, version=settings.app_version)
    try:
        await create_all_tables()
        async for db in get_db():
            await auth_manager.ensure_dev_users(db)
            await db.commit()
            break
    except Exception as exc:
        logger.warning(
            "db.create_tables_failed",
            extra={"error_type": exc.__class__.__name__},
        )
    yield
    logger.info("nexus.shutdown", extra={"service": settings.app_name})
    event_logger.emit(EVENT_SHUTDOWN, service=settings.app_name)


app = FastAPI(
    title="Nexus AI",
    description="Multi-Agent RAG Orchestration Platform",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next) -> Response:
    correlation_id = request.headers.get(CORRELATION_ID_HEADER) or generate_id()
    set_correlation_id(correlation_id)
    set_trace_id(correlation_id)
    set_log_context(correlation_id=correlation_id)
    record_request()
    start = time.monotonic()
    event_logger.emit(
        EVENT_API_REQUEST_STARTED,
        stage="api",
        component=request.url.path,
        status="success",
        method=request.method,
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.monotonic() - start) * 1000
        event_logger.emit(
            EVENT_API_REQUEST_FAILED,
            stage="api",
            component=request.url.path,
            status="fail",
            method=request.method,
            latency_ms=round(duration_ms, 2),
        )
        clear_log_context()
        raise

    response.headers[CORRELATION_ID_HEADER] = correlation_id
    response.headers["X-Trace-ID"] = correlation_id
    duration_ms = (time.monotonic() - start) * 1000
    event_logger.emit(
        EVENT_API_REQUEST_COMPLETED,
        stage="api",
        component=request.url.path,
        status="success",
        method=request.method,
        status_code=response.status_code,
        latency_ms=round(duration_ms, 2),
    )
    clear_log_context()
    return response


API_PREFIX = "/api/v1"

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(ingest.router, prefix=API_PREFIX)
app.include_router(memory.router, prefix=API_PREFIX)
app.include_router(observability.router, prefix=API_PREFIX)
app.include_router(jobs.router, prefix=API_PREFIX)
app.include_router(escalations.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(public.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", tags=["Root"])
async def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
        "ready": "/api/v1/ready",
    }
