from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest_asyncio


@pytest_asyncio.fixture
async def conflict_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from personal_pm_api.calendar.sync import CalendarSyncService
    from personal_pm_worker.calendar.adapter import ProviderEvent
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {}
    async with factory() as session:
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        user = UserModel(email="conf@example.com", display_name="X")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-conf")
        session.add(workspace)
        await session.commit()
        ids["workspace"] = str(workspace.id)

    service = CalendarSyncService(factory)

    managed = ProviderEvent(
        external_id=f"focus-{uuid4().hex[:8]}",
        title="집중 블록: 보고서",
        start_at=datetime(2026, 9, 2, 9, 0, tzinfo=UTC),
        end_at=datetime(2026, 9, 2, 10, 30, tzinfo=UTC),
        managed_focus_block=True,
    )
    imported = await service.import_event(ids["workspace"], managed)
    ids["managed"] = imported
    ids["service"] = service
    ids["factory"] = factory
    yield ids
    await engine.dispose()


async def test_external_deletion_creates_tombstone_not_immediate_hard_delete(
    conflict_env: dict[str, Any],
) -> None:
    service: Any = conflict_env["service"]
    result = await service.apply_provider_deletion(
        conflict_env["workspace"], conflict_env["managed"].external_event_id
    )
    assert result.deleted_at is not None
    assert result.sync_status == "EXTERNALLY_DELETED"


async def test_external_focus_block_move_is_not_forced_back(
    conflict_env: dict[str, Any],
) -> None:
    from personal_pm_worker.calendar.adapter import ProviderEvent

    service: Any = conflict_env["service"]
    original = conflict_env["managed"]
    moved_event = ProviderEvent(
        external_id=original.external_event_id,
        title=original.title,
        start_at=datetime(2026, 9, 2, 10, 0, tzinfo=UTC),
        end_at=datetime(2026, 9, 2, 11, 30, tzinfo=UTC),
        managed_focus_block=True,
    )
    moved = await service.apply_provider_update(conflict_env["workspace"], moved_event)
    assert moved.pending_internal_reconciliation is True
    assert moved.outbound_restore_requested is False


async def test_field_ownership_matrix() -> None:
    from personal_pm_api.calendar.field_ownership import field_owner

    assert field_owner("external_title") == "PROVIDER"
    assert field_owner("start_at") == "LAST_EXPLICIT_USER_ACTION"
    assert field_owner("task_id") == "PLANNING_CORE"
    assert field_owner("managed_marker") == "PLANNING_CORE"


async def test_recurrence_expansion_is_deterministic() -> None:
    from personal_pm_api.calendar.recurrence import expand_weekly

    start = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
    occurrences = expand_weekly(start, duration_minutes=60, count=3)
    assert len(occurrences) == 3
    assert occurrences[1].start_at == start + timedelta(weeks=1)


async def test_tombstoned_row_is_excluded_from_active_imports(
    conflict_env: dict[str, Any],
) -> None:
    service: Any = conflict_env["service"]
    ext_id = conflict_env["managed"].external_event_id
    await service.apply_provider_deletion(conflict_env["workspace"], ext_id)
    active = await service.active_events(conflict_env["workspace"])
    assert all(event.external_event_id != ext_id for event in active)


async def test_provider_deletion_is_scoped_to_workspace(conflict_env: dict[str, Any]) -> None:
    from personal_pm_api.calendar.models import ExternalCalendarEventModel
    from personal_pm_api.workspaces.models import UserModel, WorkspaceModel
    from personal_pm_worker.calendar.adapter import ProviderEvent
    from sqlalchemy import select

    factory = conflict_env["factory"]
    async with factory() as session:
        other_user = UserModel(email="conf-other@example.com", display_name="Other")
        session.add(other_user)
        await session.flush()
        other_workspace = WorkspaceModel(owner_user_id=other_user.id, name="other")
        session.add(other_workspace)
        await session.commit()
        other_workspace_id = str(other_workspace.id)

    original = conflict_env["managed"]
    await conflict_env["service"].import_event(
        other_workspace_id,
        ProviderEvent(
            external_id=original.external_event_id,
            title="다른 워크스페이스 일정",
            start_at=datetime(2026, 9, 2, 9, 0, tzinfo=UTC),
            end_at=datetime(2026, 9, 2, 10, 0, tzinfo=UTC),
            managed_focus_block=False,
        ),
    )

    await conflict_env["service"].apply_provider_deletion(
        conflict_env["workspace"], original.external_event_id
    )

    async with factory() as session:
        rows = (
            await session.execute(
                select(ExternalCalendarEventModel).where(
                    ExternalCalendarEventModel.external_event_id == original.external_event_id
                )
            )
        ).scalars()
        status_by_workspace = {str(row.workspace_id): row.sync_status for row in rows}
    assert status_by_workspace[conflict_env["workspace"]] == "EXTERNALLY_DELETED"
    assert status_by_workspace[other_workspace_id] == "SYNCED"
