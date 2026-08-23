from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError


async def _seed_workspace(db_session):
    from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

    user = UserModel(email="owner@example.com", display_name="Owner")
    db_session.add(user)
    await db_session.flush()
    workspace = WorkspaceModel(owner_user_id=user.id, name="ws")
    db_session.add(workspace)
    await db_session.flush()
    return user, workspace


async def _seed_workstream(db_session, workspace_id):
    from personal_pm_api.planning.models import WorkstreamModel

    workstream = WorkstreamModel(
        id=None,
        workspace_id=workspace_id,
        area_id=None,
        name="데이터베이스 수업",
        importance="protected",
        status="active",
        version=1,
    )
    db_session.add(workstream)
    await db_session.flush()
    return workstream


async def test_task_requires_workspace_scoped_parent(clean_tables, db_session) -> None:
    from personal_pm_api.planning.models import TaskModel

    _, workspace = await _seed_workspace(db_session)
    bogus_workstream = "00000000-0000-0000-0000-00000000dead"

    task = TaskModel(
        workspace_id=workspace.id,
        workstream_id=bogus_workstream,
        title="invalid",
        status="ready",
        base_duration_minutes=60,
        safety_duration_minutes=90,
        remaining_base_minutes=60,
        remaining_safety_minutes=90,
        uncertainty="medium",
        splittable=True,
        min_chunk_minutes=30,
        pinned=False,
        version=1,
    )
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_active_external_event_id_is_unique(clean_tables, database_url_session) -> None:
    from datetime import UTC, datetime, timedelta

    from personal_pm_api.planning.models import CalendarEventModel
    from personal_pm_api.workspaces.models import UserModel, WorkspaceModel
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as setup:
        user = UserModel(email="cal@example.com", display_name="Cal")
        setup.add(user)
        await setup.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-cal")
        setup.add(workspace)
        await setup.flush()
        workspace_id = workspace.id
        await setup.commit()

    start = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)

    def event(event_id: str) -> CalendarEventModel:
        return CalendarEventModel(
            workspace_id=workspace_id,
            external_calendar_id="cal-primary",
            external_event_id=event_id,
            external_version=1,
            title="수업",
            start_at=start,
            end_at=start + timedelta(hours=1),
            event_kind="fixed_busy",
            deadline_date=None,
            sync_status="in_sync",
            version=1,
        )

    async with factory() as first:
        first.add(event("google-1"))
        await first.flush()
        first.add(event("google-1"))
        with pytest.raises(IntegrityError):
            await first.flush()

    # A fresh unit of work sees the committed first event and accepts a new key.
    async with factory() as second:
        second.add(event("google-2"))
        await second.flush()

    await engine.dispose()


async def test_done_task_cannot_keep_remaining_minutes(clean_tables, db_session) -> None:
    from personal_pm_api.planning.models import TaskModel

    _, workspace = await _seed_workspace(db_session)
    workstream = await _seed_workstream(db_session, workspace.id)

    task = TaskModel(
        workspace_id=workspace.id,
        workstream_id=workstream.id,
        title="완료된 작업",
        status="done",
        deadline_date=None,
        deadline_at=None,
        deadline_time_known=False,
        start_after=None,
        base_duration_minutes=60,
        safety_duration_minutes=90,
        remaining_base_minutes=30,
        remaining_safety_minutes=30,
        uncertainty="low",
        splittable=True,
        min_chunk_minutes=30,
        pinned=False,
        waiting_reason=None,
        version=1,
    )
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_outbox_idempotency_key_is_unique(clean_tables, db_session) -> None:
    from personal_pm_api.execution.models import OutboxEventModel

    _, workspace = await _seed_workspace(db_session)

    def outbox(key: str) -> OutboxEventModel:
        return OutboxEventModel(
            workspace_id=workspace.id,
            operation_id=None,
            idempotency_key=key,
            command_type="CREATE_FOCUS_BLOCK",
            payload={"start": "2026-09-02T09:00:00Z"},
            status="pending",
            attempts=0,
        )

    db_session.add(outbox("idem-1"))
    await db_session.flush()
    db_session.add(outbox("idem-1"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
