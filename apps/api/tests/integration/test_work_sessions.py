from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from collections.abc import AsyncIterator
from typing import Any

import pytest_asyncio


@pytest_asyncio.fixture
async def session_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {}
    async with factory() as session:
        from personal_pm_api.planning.models import TaskModel, WorkstreamModel
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        user = UserModel(email="sess@example.com", display_name="S")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-sess")
        session.add(workspace)
        await session.flush()
        workstream = WorkstreamModel(
            workspace_id=workspace.id,
            area_id=None,
            name="ws",
            importance="normal",
            status="active",
            version=1,
        )
        session.add(workstream)
        await session.flush()
        task = TaskModel(
            workspace_id=workspace.id,
            workstream_id=workstream.id,
            milestone_id=None,
            title="세션 작업",
            status="in_progress",
            deadline_date=None,
            deadline_at=None,
            deadline_time_known=False,
            start_after=None,
            base_duration_minutes=120,
            safety_duration_minutes=150,
            remaining_base_minutes=120,
            remaining_safety_minutes=150,
            uncertainty="medium",
            splittable=True,
            min_chunk_minutes=30,
            pinned=False,
            waiting_reason=None,
            version=1,
        )
        session.add(task)
        await session.commit()
        ids["workspace"] = str(workspace.id)

        class Actor:
            user_id = "00000000-0000-0000-0000-000000000003"
            workspace_id = str(workspace.id)
            task_id = str(task.id)

        ids["factory"] = factory
        ids["actor"] = Actor()
        ids["task"] = str(task.id)

    from personal_pm_api.analytics.service import (
        EstimationProfileService,
        WorkSessionService,
    )

    ids["sessions"] = WorkSessionService(factory)
    ids["profiles"] = EstimationProfileService(factory)
    yield ids
    await engine.dispose()


async def test_partial_completion_records_actual_and_remaining_time(
    session_env: dict[str, Any],
) -> None:
    sessions: Any = session_env["sessions"]
    actor: Any = session_env["actor"]
    session_view = await sessions.start(actor, task_id=session_env["task"])
    result = await sessions.partial_complete(
        actor, session_id=session_view.id, remaining_base_minutes=50
    )
    assert result.actual_focus_minutes == 70  # 120 - 50
    assert result.task_remaining_base_minutes == 50


async def test_complete_session_zeroes_remaining(session_env: dict[str, Any]) -> None:
    sessions: Any = session_env["sessions"]
    actor: Any = session_env["actor"]
    session_view = await sessions.start(actor, task_id=session_env["task"])
    result = await sessions.complete(actor, session_id=session_view.id)
    assert result.task_remaining_base_minutes == 0


async def test_block_session_records_blocked_reason(session_env: dict[str, Any]) -> None:
    sessions: Any = session_env["sessions"]
    actor: Any = actor_fix(session_env)
    session_view = await sessions.start(actor, task_id=session_env["task"])
    result = await sessions.block(actor, session_id=session_view.id, reason="외부 의존 대기")
    assert result.status == "BLOCKED"


async def test_two_samples_do_not_change_estimation_factor(
    session_env: dict[str, Any],
) -> None:
    profiles: Any = session_env["profiles"]
    profile = await profiles.recalculate(
        session_env["workspace"], "backend", observed_ratio=2.0, sample_count=2
    )
    assert profile.factor == 1.0


async def test_many_samples_blend_observed_ratio(session_env: dict[str, Any]) -> None:
    profiles: Any = session_env["profiles"]
    profile = await profiles.recalculate(
        session_env["workspace"], "backend", observed_ratio=1.5, sample_count=10
    )
    # weight for 10 samples = 0.60 → factor = 1 + (1.5-1)*0.60
    assert profile.factor == pytest.approx(1.30)

    clamped_low = await profiles.recalculate(
        session_env["workspace"], "x", observed_ratio=0.1, sample_count=20
    )
    assert clamped_low.factor >= 0.75

    clamped_high = await profiles.recalculate(
        session_env["workspace"], "y", observed_ratio=9.9, sample_count=25
    )
    assert clamped_high.factor <= 2.5


def actor_fix(env: dict[str, Any]) -> Any:
    return env["actor"]
