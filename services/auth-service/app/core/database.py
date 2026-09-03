"""Async SQLAlchemy database engine, session factory, and Base model."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ─── 1. Async Engine ──────────────────────────────────────────────────
engine_kwargs = {
    "echo": settings.DEBUG,
}

if "sqlite" in settings.DATABASE_URL:
    from sqlalchemy.pool import StaticPool

    engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    })
else:
    engine_kwargs.update({
        "pool_pre_ping": True,       # Test connection health before reusing from pool
        "pool_size": 10,             # Maintain up to 10 persistent DB connections
        "max_overflow": 20,          # Allow up to 20 temporary extra connections under load
        "pool_recycle": 3600,        # Recycle connections every hour to prevent stale sockets
    })

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

# ─── 2. Session Factory ───────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # Keep model object attributes accessible after commit
    autoflush=True,
    autocommit=False,
)


# ─── 3. Declarative Base ──────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# ─── 4. FastAPI Database Dependency ──────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per HTTP request.
    Automatically commits on success, rolls back on exception, and closes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()