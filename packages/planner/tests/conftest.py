"""Shared planner fixtures used across unit suites."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from personal_pm_planner.domain.availability import AvailabilityWindow
from personal_pm_planner.domain.dependency import TaskDependency
from personal_pm_planner.domain.enums import DeadlineType, DependencyType, TaskStatus
from personal_pm_planner.domain.identifiers import (
    MilestoneId,
    TaskId,
    WorkspaceId,
    WorkstreamId,
)
from personal_pm_planner.domain.task import TaskSnapshot
from personal_pm_planner.domain.work import MilestoneSnapshot

WORKSPACE = WorkspaceId(UUID("00000000-0000-0000-0000-000000000001"))
WORKSTREAM = WorkstreamId(UUID("00000000-0000-0000-0000-000000000100"))
MILESTONE = MilestoneId(UUID("00000000-0000-0000-0000-000000000200"))
NOW_UTC = datetime(2026, 8, 23, 3, 0, tzinfo=UTC)


def make_task(
    offset: int,
    *,
    status: TaskStatus = TaskStatus.READY,
    base: int = 60,
    safety: int | None = None,
    uncertainty: str = "medium",
    splittable: bool = True,
    deadline_date: date | None = date(2026, 9, 10),
) -> TaskSnapshot:
    safety_minutes = safety if safety is not None else base + 30
    return TaskSnapshot(
        id=TaskId(UUID(int=offset)),
        workspace_id=WORKSPACE,
        workstream_id=WORKSTREAM,
        milestone_id=MILESTONE,
        title=f"task-{offset}",
        status=status,
        deadline_date=deadline_date,
        deadline_at=None,
        deadline_time_known=False,
        start_after=None,
        base_duration_minutes=base,
        safety_duration_minutes=safety_minutes,
        remaining_base_minutes=base,
        remaining_safety_minutes=safety_minutes,
        uncertainty=uncertainty,
        splittable=splittable,
        min_chunk_minutes=30,
        pinned=False,
        waiting_reason=None,
        version=1,
    )


def make_milestone(**overrides: object) -> MilestoneSnapshot:
    defaults: dict[str, object] = {
        "id": MILESTONE,
        "workspace_id": WORKSPACE,
        "workstream_id": WORKSTREAM,
        "title": "제출",
        "deadline_date": date(2026, 9, 10),
        "deadline_at": None,
        "deadline_date_known": True,
        "deadline_time_known": False,
        "deadline_type": DeadlineType.HARD_DEADLINE,
        "required_buffer_minutes": 60,
        "version": 1,
    }
    defaults.update(overrides)
    return MilestoneSnapshot(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def date_only_milestone() -> MilestoneSnapshot:
    return make_milestone(deadline_time_known=False)


@pytest.fixture
def milestone_factory():
    return make_milestone


@pytest.fixture
def planner_input_factory():
    def factory(
        *,
        reverse_tasks: bool = False,
        done_task_remaining: int | None = None,
        task_count: int = 5,
        availability_hours: int = 4,
    ):
        from personal_pm_planner.contracts.input import PlannerInput

        tasks = [make_task(offset) for offset in range(1, task_count + 1)]
        if done_task_remaining is not None:
            target = tasks[0]
            object.__setattr__(target, "status", TaskStatus.DONE)
            object.__setattr__(target, "remaining_base_minutes", done_task_remaining)
            object.__setattr__(target, "remaining_safety_minutes", done_task_remaining)
        if reverse_tasks:
            tasks.reverse()
        return PlannerInput(
            planner_version="planner-spec-1.0",
            now_utc=NOW_UTC,
            user_timezone="Asia/Seoul",
            horizon_end_utc=NOW_UTC + timedelta(days=14),
            slot_minutes=15,
            availability_windows=(
                AvailabilityWindow(
                    start_at=NOW_UTC,
                    end_at=NOW_UTC + timedelta(hours=availability_hours),
                    tags=frozenset({"focus"}),
                ),
            ),
            calendar_events=(),
            tasks=tuple(tasks),
            milestones=(make_milestone(),),
            task_dependencies=(
                TaskDependency(
                    TaskId(UUID(int=1)),
                    TaskId(UUID(int=2)),
                    DependencyType.BLOCKS_START,
                ),
            ),
            external_dependencies=(),
            pinned_task_ids=frozenset(),
            excluded_dates=(),
            prior_plan_snapshot=None,
        )

    return factory
