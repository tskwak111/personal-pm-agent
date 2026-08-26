from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

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
        from sqlalchemy import text as _text

        await session.execute(_text("delete from users where email = 'plan@example.com'"))
        await session.flush()
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


async def _make_service(env: dict[str, Any]):
    from personal_pm_api.planning.service import PlanningService
    from sqlalchemy.ext.asyncio import AsyncSession

    session: AsyncSession = env["factory"]()
    service = PlanningService(session)
    return service, session


async def test_valid_plan_appends_current_snapshot(planning_env) -> None:
    service, session = await _make_service(planning_env)
    try:
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
        assert str(latest.id) == dto.id
        assert latest.is_current is True
    finally:
        await session.close()


async def test_invalid_plan_preserves_last_valid_snapshot(planning_env, monkeypatch) -> None:
    service_before, session_before = await _make_service(planning_env)
    try:
        first = await service_before.create_plan(
            actor_user_id=None, workspace_id=planning_env["workspace"], reason="first"
        )
        assert first.status == "OK"
    finally:
        await session_before.close()

    # Force INVALID_INPUT without violating DB CHECKs: patch normalization to
    # return a typed failure. This proves PLAN-009 preservation without needing
    # corrupt DB rows (which would be blocked by CHECK constraints).
    from personal_pm_planner.normalization.validate import InvalidPlannerInput

    def fake_normalize(_inp):  # type: ignore[no-untyped-def]
        return InvalidPlannerInput(
            error_code="INVALID_INPUT",
            rule_ids=("DONE_TASK_HAS_REMAINING_TIME",),
            prior_plan_snapshot=None,
        )

    service_after, session_after = await _make_service(planning_env)
    monkeypatch.setattr("personal_pm_api.planning.service.normalize_and_validate", fake_normalize)
    try:
        result = await service_after.create_plan(
            actor_user_id=None,
            workspace_id=UUID(str(planning_env["workspace"])),
            reason="should-fail",
        )
        assert result.status == "INVALID_INPUT"

        latest = await service_after.latest_valid(planning_env["workspace"])
        assert latest is not None
        assert str(latest.id) == first.id
    finally:
        await session_after.close()
