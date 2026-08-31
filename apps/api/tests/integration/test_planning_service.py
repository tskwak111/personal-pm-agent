from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
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


async def test_build_planner_input_hydrates_persisted_workspace_facts(planning_env) -> None:
    from personal_pm_api.planning.models import (
        CalendarEventModel,
        ExternalDependencyModel,
        ExternalDependencyTaskModel,
        PlanSnapshotModel,
        TaskDependencyModel,
        TaskModel,
        WorkspaceExcludedDateModel,
    )
    from personal_pm_api.workspaces.models import WorkspaceModel
    from personal_pm_planner.domain.enums import CalendarEventKind, DependencyType
    from personal_pm_planner.domain.identifiers import TaskId

    service, session = await _make_service(planning_env)
    try:
        workspace_id = UUID(planning_env["workspace"])
        workstream_id = UUID(planning_env["workstream"])
        milestone_id = UUID(planning_env["milestone"])
        workspace = await session.get(WorkspaceModel, workspace_id)
        assert workspace is not None
        workspace.timezone = "America/New_York"

        def task(title: str, *, pinned: bool = False) -> TaskModel:
            return TaskModel(
                workspace_id=workspace_id,
                workstream_id=workstream_id,
                milestone_id=milestone_id,
                title=title,
                status="ready",
                deadline_date=None,
                deadline_at=None,
                deadline_time_known=False,
                start_after=None,
                base_duration_minutes=60,
                safety_duration_minutes=90,
                remaining_base_minutes=60,
                remaining_safety_minutes=90,
                uncertainty="medium",
                splittable=True,
                min_chunk_minutes=30,
                pinned=pinned,
                waiting_reason=None,
                version=1,
            )

        predecessor = task("선행", pinned=True)
        successor = task("후행")
        session.add_all((predecessor, successor))
        await session.flush()

        start = datetime(2026, 9, 1, 13, 0, tzinfo=UTC)
        external = ExternalDependencyModel(
            workspace_id=workspace_id,
            deliverable="검토 결과",
            owner_label="리뷰어",
            expected_delivery_at=start + timedelta(hours=2),
            uncertainty_buffer_minutes=30,
            fallback_available=True,
            version=1,
        )
        session.add(external)
        await session.flush()
        session.add_all(
            (
                CalendarEventModel(
                    workspace_id=workspace_id,
                    external_calendar_id="primary",
                    external_event_id="event-1",
                    external_version=1,
                    title="고정 회의",
                    start_at=start,
                    end_at=start + timedelta(hours=1),
                    event_kind=CalendarEventKind.FIXED_BUSY.value,
                    deadline_date=None,
                    sync_status="in_sync",
                    version=1,
                ),
                TaskDependencyModel(
                    workspace_id=workspace_id,
                    predecessor_id=predecessor.id,
                    successor_id=successor.id,
                    dependency_type=DependencyType.BLOCKS_START.value,
                ),
                ExternalDependencyTaskModel(
                    workspace_id=workspace_id,
                    external_dependency_id=external.id,
                    task_id=successor.id,
                    role="affected",
                ),
                ExternalDependencyTaskModel(
                    workspace_id=workspace_id,
                    external_dependency_id=external.id,
                    task_id=predecessor.id,
                    role="fallback",
                ),
                WorkspaceExcludedDateModel(
                    workspace_id=workspace_id,
                    excluded_date=date(2026, 9, 7),
                ),
                PlanSnapshotModel(
                    workspace_id=workspace_id,
                    planner_version="planner-spec-1.0",
                    input_hash="a" * 64,
                    reason="prior",
                    output_json={
                        "base_allocations": [
                            {
                                "task_id": predecessor.id.hex,
                                "start": start.isoformat(),
                                "end": (start + timedelta(hours=1)).isoformat(),
                            }
                        ]
                    },
                    is_current=True,
                ),
            )
        )
        await session.commit()

        captured = await service._build_planner_input(workspace_id, start)

        assert captured.user_timezone == "America/New_York"
        assert len(captured.calendar_events) == 1
        assert len(captured.task_dependencies) == 1
        assert len(captured.external_dependencies) == 1
        assert captured.external_dependencies[0].affected_task_ids == (TaskId(successor.id),)
        assert captured.external_dependencies[0].fallback_task_ids == (TaskId(predecessor.id),)
        assert captured.pinned_task_ids == frozenset({TaskId(predecessor.id)})
        assert captured.excluded_dates == (date(2026, 9, 7),)
        assert captured.prior_plan_snapshot is not None
        assert captured.prior_plan_snapshot.allocations[0].task_id == TaskId(predecessor.id)
    finally:
        await session.close()


async def test_malformed_prior_plan_is_rejected_without_replacing_it(planning_env) -> None:
    from personal_pm_api.planning.models import PlanSnapshotModel

    service, session = await _make_service(planning_env)
    try:
        current = PlanSnapshotModel(
            workspace_id=UUID(planning_env["workspace"]),
            planner_version="planner-spec-1.0",
            input_hash="b" * 64,
            reason="malformed-prior",
            output_json={"base_allocations": [{"task_id": "not-a-uuid"}]},
            is_current=True,
        )
        session.add(current)
        await session.commit()

        with pytest.raises(ValueError, match="allocation fields"):
            await service.create_plan(
                actor_user_id=None,
                workspace_id=planning_env["workspace"],
                reason="must-not-replace",
            )

        latest = await service.latest_valid(planning_env["workspace"])
        assert latest is not None
        assert latest.id == current.id
        assert latest.is_current is True
    finally:
        await session.close()
