from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest_asyncio


@pytest_asyncio.fixture
async def sync_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {}
    async with factory() as session:
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        user = UserModel(email="sync@example.com", display_name="S")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-sync")
        session.add(workspace)
        await session.commit()
        ids["workspace"] = str(workspace.id)

    from personal_pm_api.calendar.sync import CalendarSyncService

    ids["factory"] = factory
    ids["service"] = CalendarSyncService(factory)
    yield ids
    await engine.dispose()


def _provider_event(**overrides: Any) -> Any:
    base = {
        "external_id": f"evt-{uuid4().hex[:8]}",
        "title": "수업",
        "start_at": datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
        "end_at": datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
        "all_day": False,
        "blocks_time": True,
        "status": "confirmed",
        "managed_focus_block": False,
        "transparency": "opaque",
    }
    merged = {**base, **overrides}

    from personal_pm_worker.calendar.adapter import ProviderEvent

    return ProviderEvent(**merged)


async def _count_events(factory: Any, external_id: str) -> int:
    from personal_pm_api.calendar.models import ExternalCalendarEventModel
    from sqlalchemy import select

    async with factory() as session:
        rows = (
            (
                await session.execute(
                    select(ExternalCalendarEventModel).where(
                        ExternalCalendarEventModel.external_event_id == external_id
                    )
                )
            )
            .scalars()
            .all()
        )
    return len(rows)


async def test_all_day_information_does_not_block_full_day(sync_env: dict[str, Any]) -> None:
    service: Any = sync_env["service"]
    event = _provider_event(all_day=True, blocks_time=False, transparency="transparent")
    imported = await service.import_event(sync_env["workspace"], event)
    assert imported.availability_type == "ALL_DAY_INFORMATION"
    assert imported.blocks_capacity is False


async def test_same_external_id_updates_existing_record(sync_env: dict[str, Any]) -> None:
    service: Any = sync_env["service"]
    wid = sync_env["workspace"]
    first = await service.import_event(wid, _provider_event(external_id="e1", title="old"))
    second = await service.import_event(wid, _provider_event(external_id="e1", title="new"))
    assert second.id == first.id
    assert second.title == "new"
    assert await _count_events(sync_env["factory"], "e1") == 1


async def test_busy_confirmed_event_maps_to_fixed_busy(sync_env: dict[str, Any]) -> None:
    service: Any = sync_env["service"]
    imported = await service.import_event(sync_env["workspace"], _provider_event())
    assert imported.availability_type == "FIXED_BUSY"
    assert imported.blocks_capacity is True


async def test_tentative_event_maps_to_tentative(sync_env: dict[str, Any]) -> None:
    service: Any = sync_env["service"]
    imported = await service.import_event(
        sync_env["workspace"], _provider_event(status="tentative")
    )
    assert imported.availability_type == "TENTATIVE"
