"""Async engine and session factories for the canonical PostgreSQL store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from personal_pm_api.settings import ApiSettings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: ApiSettings | None = None) -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        app_settings = settings if settings is not None else ApiSettings()
        _engine = create_async_engine(app_settings.database_url, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine


def session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


@asynccontextmanager
async def database_session() -> AsyncIterator[AsyncSession]:
    """Yield a session; roll back on exception so callers never half-commit."""
    factory = session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
