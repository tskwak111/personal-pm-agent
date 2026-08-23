from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

import os

import sqlalchemy as sa


def database_url() -> str:
    return os.environ.get(
        "PM_DATABASE_URL",
        "postgresql+asyncpg://personal_pm:local_only_password@localhost:15432/personal_pm",
    )


async def test_database_session_rolls_back_uncommitted_change(
    migrated_database, database_url_session
) -> None:
    from personal_pm_api.shared.db import database_session as app_database_session
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(database_url_session, pool_pre_ping=True)

    async with app_database_session() as session:
        # Probe table is created and committed on this very session; only the
        # INSERT afterwards stays uncommitted.
        await session.execute(sa.text("create temporary table rollback_probe(value int)"))
        await session.commit()
        await session.execute(sa.text("insert into rollback_probe values (1)"))
        await session.rollback()
        count = await session.scalar(sa.text("select count(*) from rollback_probe"))
        assert count == 0
    await engine.dispose()


async def test_settings_default_to_local_compose_postgres() -> None:
    assert "postgresql+asyncpg://" in database_url()
