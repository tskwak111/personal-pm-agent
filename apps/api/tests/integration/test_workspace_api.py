from __future__ import annotations

import os
import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def workspace_api(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from personal_pm_api.main import create_app
    from personal_pm_api.shared.db import reset_engine
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    app = create_app()
    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {}
    async with factory() as session:
        from personal_pm_api.identity.models import UserSessionModel
        from personal_pm_api.identity.session import hash_session_token
        from personal_pm_api.planning.models import MilestoneModel, TaskModel, WorkstreamModel
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        raw_token = secrets.token_urlsafe(32)
        user = UserModel(email="ws-api@example.com", display_name="WS")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws")
        session.add(workspace)
        await session.flush()
        session.add(
            UserSessionModel(
                user_id=user.id,
                token_hash=hash_session_token(raw_token),
                expires_at=datetime.now(UTC) + timedelta(hours=8),
            )
        )
        workstream = WorkstreamModel(
            workspace_id=workspace.id,
            area_id=None,
            name="API 수업",
            importance="protected",
            status="active",
            version=1,
        )
        session.add(workstream)
        await session.flush()
        milestone = MilestoneModel(
            workspace_id=workspace.id,
            workstream_id=workstream.id,
            title="과제 제출",
            deadline_date=datetime(2026, 9, 10).date(),
            deadline_at=datetime(2026, 9, 10, 3, 0, tzinfo=UTC),
            deadline_date_known=True,
            deadline_time_known=True,
            deadline_type="hard_deadline",
            required_buffer_minutes=30,
            version=1,
        )
        session.add(milestone)

        def make_task(offset: int, *, base: int, safety: int, status: str = "ready"):
            return TaskModel(
                workspace_id=workspace.id,
                workstream_id=workstream.id,
                milestone_id=milestone.id,
                title=f"task-{offset}",
                status=status,
                deadline_date=None,
                deadline_at=None,
                deadline_time_known=False,
                start_after=None,
                base_duration_minutes=base,
                safety_duration_minutes=safety,
                remaining_base_minutes=base,
                remaining_safety_minutes=safety,
                uncertainty="medium",
                splittable=True,
                min_chunk_minutes=30,
                pinned=False,
                waiting_reason=None,
                version=1,
            )

        ready_task = make_task(1, base=60, safety=90, status="in_progress")
        ready_task.remaining_base_minutes = 0
        ready_task.remaining_safety_minutes = 0
        heavy_task = make_task(2, base=120, safety=150, status="in_progress")
        date_only_task = make_task(3, base=60, safety=75, status="ready")

        session.add_all([ready_task, heavy_task, date_only_task])
        await session.commit()

        ids.update(
            app=app,
            engine=engine,
            token=raw_token,
            workspace=str(workspace.id),
            milestone=str(milestone.id),
            done_ready_task=str(ready_task.id),
            heavy_task=str(heavy_task.id),
        )

    transport = ASGITransport(app=app)
    client = AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {ids['token']}"},
    )
    try:
        yield {**ids, "client": client}
    finally:
        await client.aclose()
        await engine.dispose()
        await reset_engine()


async def test_task_completion_uses_domain_state_machine(
    workspace_api: dict[str, Any],
) -> None:
    client: AsyncClient = workspace_api["client"]
    response = await client.post(
        f"/api/v1/tasks/{workspace_api['done_ready_task']}/transition",
        json={
            "expected_version": 1,
            "target_status": "DONE",
            "completion_confirmed": True,
        },
    )
    assert response.status_code == 200


async def test_done_with_remaining_minutes_is_rejected_with_typed_code(
    workspace_api: dict[str, Any],
) -> None:
    client: AsyncClient = workspace_api["client"]
    response = await client.post(
        f"/api/v1/tasks/{workspace_api['heavy_task']}/transition",
        json={
            "expected_version": 1,
            "target_status": "DONE",
            "completion_confirmed": True,
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "TASK_HAS_REMAINING_TIME"


async def test_forbidden_transition_is_422(workspace_api: dict[str, Any]) -> None:
    client: AsyncClient = workspace_api["client"]
    # draft -> in_progress is not an allowed edge.
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_of())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        task_id = await _insert_draft(session, workspace_api["workspace"])
    await engine.dispose()

    response = await client.post(
        f"/api/v1/tasks/{task_id}/transition",
        json={"expected_version": 1, "target_status": "IN_PROGRESS"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_TRANSITION"


def database_url_of() -> str:

    return os.environ["DATABASE_URL"]


async def _insert_draft(session, workspace_id: str) -> str:
    from personal_pm_api.planning.models import TaskModel, WorkstreamModel
    from sqlalchemy import select

    ws = (
        (
            await session.execute(
                select(WorkstreamModel).where(WorkstreamModel.workspace_id == UUID(workspace_id))
            )
        )
        .scalars()
        .first()
    )
    task = TaskModel(
        workspace_id=UUID(workspace_id),
        workstream_id=ws.id,
        milestone_id=None,
        title="draft-task",
        status="draft",
        deadline_date=None,
        deadline_at=None,
        deadline_time_known=False,
        start_after=None,
        base_duration_minutes=60,
        safety_duration_minutes=90,
        remaining_base_minutes=60,
        remaining_safety_minutes=90,
        uncertainty="low",
        splittable=True,
        min_chunk_minutes=30,
        pinned=False,
        waiting_reason=None,
        version=1,
    )
    session.add(task)
    await session.commit()
    return str(task.id)


async def test_hard_deadline_change_creates_proposal(
    workspace_api: dict[str, Any],
) -> None:
    client: AsyncClient = workspace_api["client"]
    response = await client.patch(
        f"/api/v1/milestones/{workspace_api['milestone']}",
        json={"expected_version": 1, "deadline_date": "2026-09-11"},
    )
    assert response.status_code == 202
    body = response.json()["proposal"]
    assert body["authorization_level"] == "RECONFIRM"
    assert body["status"] == "pending"
