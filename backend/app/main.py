from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import health, chat, ingest, memory, observability
from app.core.config import settings
from app.core.ids import generate_id, set_correlation_id
from app.core.logger import get_logger, set_log_context, clear_log_context
from app.services.events import logger as event_logger
from app.services.events.types import EVENT_STARTUP, EVENT_SHUTDOWN

logger = get_logger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "nexus.startup",
        extra={"service": settings.app_name, "version": settings.app_version, "env": settings.app_env},
    )
    event_logger.emit(EVENT_STARTUP, service=settings.app_name, version=settings.app_version)
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

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Correlation ID Middleware ────────────────────────────────────────────────
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next) -> Response:
    """
    Propagate or generate a correlation ID for every request.

    - If the incoming request has X-Correlation-ID, use it.
    - Otherwise generate a new UUID4.
    - The ID is set in the request context and returned in the response header.
    """
    correlation_id = request.headers.get(CORRELATION_ID_HEADER) or generate_id()
    set_correlation_id(correlation_id)
    set_log_context(correlation_id=correlation_id)

    response = await call_next(request)

    response.headers[CORRELATION_ID_HEADER] = correlation_id
    clear_log_context()
    return response


# ─── Routes ──────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(ingest.router, prefix=API_PREFIX)
app.include_router(memory.router, prefix=API_PREFIX)
app.include_router(observability.router, prefix=API_PREFIX)


@app.get("/", tags=["Root"])
async def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
