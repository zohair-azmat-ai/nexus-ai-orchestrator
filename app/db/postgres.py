from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logger import get_logger, sanitize_log_value

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
        await _ensure_runtime_schema(conn)
    logger.info("db.tables_created")


async def _ensure_runtime_schema(conn) -> None:
    def _has_column(sync_conn, table_name: str, column_name: str) -> bool:
        inspector = inspect(sync_conn)
        columns = inspector.get_columns(table_name)
        return any(column["name"] == column_name for column in columns)

    has_plan = await conn.run_sync(_has_column, "users", "plan")
    if has_plan:
        return

    dialect = conn.engine.dialect.name
    if dialect == "postgresql":
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(32) NOT NULL DEFAULT 'free'"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_plan ON users (plan)"))
    elif dialect == "sqlite":
        await conn.execute(text("ALTER TABLE users ADD COLUMN plan VARCHAR(32) NOT NULL DEFAULT 'free'"))


async def check_postgres_connection() -> bool:
    """Health-check helper: returns True if DB is reachable."""
    try:
        from sqlalchemy import text

        async with _get_session_local()() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning(
            "db.health_check_failed",
            extra={"error_type": exc.__class__.__name__, "detail": sanitize_log_value(str(exc))},
        )
        return False
