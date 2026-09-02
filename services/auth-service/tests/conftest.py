"""Pytest configuration and shared test fixtures.

Uses SQLite in-memory DB and mocked Redis for fast, isolated unit tests.
"""
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set TESTING environment variable BEFORE importing app modules
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-min-32-chars"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["REDIS_PASSWORD"] = ""

from app.core.database import Base, get_db
from app.main import app
from app.utils.deps import get_redis

# ─── 1. In-Memory SQLite Engine Setup ─────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─── 2. Database Fixtures ─────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create all database tables in memory once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Provides a clean, isolated database session per test (rolled back after)."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ─── 3. Mocked Redis Fixture ──────────────────────────────────────────
@pytest_asyncio.fixture
async def mock_redis() -> AsyncMock:
    """Mock Redis client so tests do not require a live Redis container."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.aclose = AsyncMock()
    return redis


# ─── 4. Async HTTP Client Fixture ─────────────────────────────────────
@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Provides an async HTTP test client with database and Redis dependency overrides."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_get_redis() -> AsyncGenerator[AsyncMock, None]:
        yield mock_redis

    # Apply FastAPI dependency overrides
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    # Clean up overrides after test
    app.dependency_overrides.clear()