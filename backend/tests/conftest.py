"""
Test configuration — overrides the database dependency with an
in-memory SQLite instance so tests run without a live Postgres server.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401 — registers all ORM models on Base.metadata
from app.db.postgres import Base, get_db
from app.main import app

SQLITE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function", autouse=True)
async def override_db():
    """
    Create an isolated SQLite in-memory database for each test function.
    Overrides the `get_db` FastAPI dependency for the duration of the test.
    """
    engine = create_async_engine(SQLITE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_test_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db

    yield

    app.dependency_overrides.pop(get_db, None)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
