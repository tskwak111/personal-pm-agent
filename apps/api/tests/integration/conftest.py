"""Integration test fixtures backed by the local compose PostgreSQL."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text

DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://personal_pm:local_only_password@localhost:15432/personal_pm"
)


def database_url() -> str:
    return os.environ.get("PM_DATABASE_URL", DEFAULT_DATABASE_URL)


@pytest.fixture(scope="session")
def database_url_session() -> str:
    return database_url()


@pytest.fixture
async def db_session(database_url_session: str) -> AsyncIterator:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(scope="session")
def migrated_database(database_url_session: str):
    """Run migrations to head; teardown rolls back to base for repeatability."""
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[2]  # apps/api
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    url = database_url_session.replace("+asyncpg", "+psycopg")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    yield
    command.downgrade(config, "base")


@pytest_asyncio.fixture
async def clean_tables(migrated_database, db_session):  # noqa: ANN201
    """Truncate all planning-core tables between integration tests."""
    yield
    await db_session.execute(
        text(
            "TRUNCATE TABLE audit_events, outbox_events, external_executions, "
            "approvals, proposals, plan_snapshots, task_dependencies, tasks, "
            "milestones, workstreams, areas, calendar_events, availability_windows, "
            "workspaces, users CASCADE"
        )
    )
    await db_session.commit()
