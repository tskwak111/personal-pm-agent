from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import UUID

import pytest_asyncio


@pytest_asyncio.fixture
async def planning_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {"engine": engine, "factory": factory}
    async with factory() as session:
        from personal_pm_api.planning.models import MilestoneModel, WorkstreamModel
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        user = UserModel(email="plan@example.com", display_name="P")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-plan")
        session.add(workspace)
        await session.flush()
        workstream = WorkstreamModel(
            workspace_id=workspace.id,
            area_id=None,
            name="계획 수업",
            importance="important",
            status="active",
            version=1,
        )
        session.add(workstream)
        await session.flush()
        milestone = MilestoneModel(
            workspace_id=workspace.id,
            workstream_id=workstream.id,
            title="제출 마감",
            deadline_date=datetime(2026, 9, 20).date(),
            deadline_at=None,
            deadline_date_known=True,
            deadline_time_known=False,
            deadline_type="hard_deadline",
            required_buffer_minutes=30,
            version=1,
        )
        session.add(milestone)
        await session.commit()

        ids["user"] = str(user.id)
        ids["workspace"] = str(workspace.id)
        ids["workstream"] = str(workstream.id)
        ids["milestone"] = str(milestone.id)
    yield ids
    await engine.dispose()


async def _make_service(env: dict[str, Any], *, break_task: bool = False):
    from personal_pm_api.planning.service import PlanningService
    from sqlalchemy.ext.asyncio import AsyncSession

    session: AsyncSession = env["factory"]()
    if break_task:
        from sqlalchemy import text

        await session.execute(
            text(
                "insert into tasks (id, workspace_id, workstream_id, milestone_id, title,"
                " status, deadline_date, deadline_at, deadline_time_known,"
                " base_duration_minutes, safety_duration_minutes,"
                " remaining_base_minutes, remaining_safety_minutes, uncertainty,"
                " splittable, min_chunk_minutes, pinned, version)"
                " values (gen_random_uuid(), :ws, :wsn, null, 'broken', 'done',"
                " null, null, false, 60, 90, 15, 15, 'medium', true, 30, false, 1)"
            ),
            {"ws": env["workspace"], "wsn": env["workstream"]},
        )
        await session.commit()
    service = PlanningService(session)
    return service, session


async def test_valid_plan_appends_current_snapshot(planning_env) -> None:
    service, _ = await _make_service(planning_env)

    dto = await service.create_plan(
        actor_user_id=None,
        workspace_id=planning_env["workspace"],
        reason="test",
    )
    assert dto.status == "OK"
    assert dto.planner_version == "planner-spec-1.0"
    assert len(dto.input_hash) == 64

    latest = await service.latest_valid(planning_env["workspace"])
    assert latest is not None
    assert latest.id == dto.id
    assert latest.is_current is True


async def test_invalid_plan_preserves_last_valid_snapshot(planning_env) -> None:
    service_before, _ = await _make_service(planning_env)
    first = await service_before.create_plan(
        actor_user_id=None, workspace_id=planning_env["workspace"], reason="first"
    )
    assert first.status == "OK"

    # Corrupt state: done task with remaining minutes -> INVALID_INPUT rule.
    service_after, session_after = await _make_service(planning_env, break_task=True)
    from personal_pm_api.planning.models import TaskModel

    broken = TaskModel(
        workspace_id=UUID(str(planning_env["workspace"])),
        workstream_id=UUID(str(planning_env["workstream"])),
        milestone_id=None,
        title="broken",
        status="done",
        deadline_date=None,
        deadline_at=None,
        deadline_time_known=False,
        start_after=None,
        base_duration_minutes=60,
        safety_duration_minutes=90,
        remaining_base_minutes=15,
        remaining_safety_minutes=15,
        uncertainty="medium",
        splittable=True,
        min_chunk_minutes=30,
        pinned=False,
        waiting_reason=None,
        version=1,
    )
    session_after.add(broken)
    await session_after.commit()
    await session_after.close()

    result = await service_after.create_plan(
        actor_user_id=None,
        workspace_id=UUID(str(planning_env["workspace"])),
        reason="should-fail",
    )
    assert result.status == "INVALID_INPUT"

    latest = await service_after.latest_valid(planning_env["workspace"])
    assert latest is not None
    assert str(latest.id) == first.id
