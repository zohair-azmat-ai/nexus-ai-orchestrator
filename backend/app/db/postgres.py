from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


# ─── Lazy engine + session factory ───────────────────────────────────────────
# The engine is NOT created at import time so that:
#   a) test overrides via dependency injection work without loading the Postgres driver
#   b) misconfigured DB URLs don't crash the process on startup

_engine: "AsyncEngine | None" = None
_session_local: async_sessionmaker | None = None


def _get_engine() -> "AsyncEngine":
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def _get_session_local() -> async_sessionmaker:
    global _session_local
    if _session_local is None:
        _session_local = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_local


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with _get_session_local()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """Create all ORM tables if they do not exist. Safe to call on startup."""
    import app.db.models  # noqa: F401 — registers models on Base.metadata

    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("db.tables_created")


async def check_postgres_connection() -> bool:
    """Health-check helper: returns True if DB is reachable."""
    try:
        from sqlalchemy import text

        async with _get_session_local()() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Postgres health check failed", extra={"error": str(exc)})
        return False
