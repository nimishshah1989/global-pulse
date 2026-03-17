"""Async SQLAlchemy engine and session factory.

Supports both SQLite (development) and PostgreSQL (production).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the global async engine, creating it on first call."""
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    url = settings.DATABASE_URL

    kwargs: dict = {
        "echo": settings.is_development,
    }

    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = 20
        kwargs["max_overflow"] = 10
        kwargs["pool_pre_ping"] = True

    _engine = create_async_engine(url, **kwargs)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the global session factory, creating it on first call."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory

    _session_factory = async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return _session_factory


# Backwards compatibility: module-level references
engine = property(lambda self: get_engine())  # type: ignore


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Ensures the session is properly closed after use.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
