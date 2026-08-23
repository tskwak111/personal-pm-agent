"""Reference-vector input builders shared by JSON vector definitions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from personal_pm_planner.contracts.input import (
    PlannerInput,
    PriorAllocation,
    PriorPlanSnapshot,
)
from personal_pm_planner.domain.availability import (
    AvailabilityWindow,
    ExternalDependencySnapshot,
)
from personal_pm_planner.domain.dependency import TaskDependency
from personal_pm_planner.domain.enums import DeadlineType, DependencyType
from personal_pm_planner.domain.identifiers import (
    ExternalDependencyId,
    MilestoneId,
    TaskId,
    WorkspaceId,
    WorkstreamId,
)
from personal_pm_planner.domain.task import TaskSnapshot
from personal_pm_planner.domain.work import MilestoneSnapshot

NOW = datetime(2026, 9, 1, 0, 30, tzinfo=UTC)
DEADLINE = datetime(2026, 9, 10, 3, 0, tzinfo=UTC)
WORKSPACE = WorkspaceId(UUID("00000000-0000-0000-0000-000000000001"))
WORKSTREAM = WorkstreamId(UUID("00000000-0000-0000-0000-000000000100"))
MILESTONE_ID = MilestoneId(UUID("00000000-0000-0000-0000-000000000200"))


def _task(
    offset: int,
    *,
    base: int,
    safety: int,
    status: str = "ready",
    splittable: bool = True,
) -> TaskSnapshot:
    from personal_pm_planner.domain.enums import TaskStatus

    return TaskSnapshot(
        id=TaskId(UUID(int=offset)),
        workspace_id=WORKSPACE,
        workstream_id=WORKSTREAM,
        milestone_id=MILESTONE_ID,
        title=f"task-{offset}",
        status=TaskStatus(status),
        deadline_date=None,
        deadline_at=DEADLINE,
        deadline_time_known=True,
        start_after=None,
        base_duration_minutes=base,
        safety_duration_minutes=safety,
        remaining_base_minutes=base if status != "done" else 0,
        remaining_safety_minutes=safety if status != "done" else 0,
        uncertainty="medium",
        splittable=splittable,
        min_chunk_minutes=30,
        pinned=False,
        waiting_reason=None,
        version=1,
    )


def build_vector_input(spec: dict) -> PlannerInput:
    tasks_spec = spec.get("tasks", [])
    tasks = tuple(
        _task(
            index,
            base=item.get("base", 60),
            safety=item.get("safety", item.get("base", 60) + 30),
            status=item.get("status", "ready"),
            splittable=item.get("splittable", True),
        )
        for index, item in enumerate(tasks_spec, start=1)
    )

    dependencies_list: list[TaskDependency] = []
    if spec.get("cycle"):
        ids = [task.id for task in tasks[:3]]
        if len(ids) >= 2:
            for i in range(len(ids)):
                dependencies_list.append(
                    TaskDependency(ids[i], ids[(i + 1) % len(ids)], DependencyType.BLOCKS_START)
                )
    for predecessor, successor in spec.get("blocks_completion", []):
        dependencies_list.append(
            TaskDependency(
                TaskId(UUID(int=predecessor)),
                TaskId(UUID(int=successor)),
                DependencyType.BLOCKS_COMPLETION,
            )
        )
    dependencies = tuple(dependencies_list)

    external_spec = spec.get("external")
    externals = ()
    if external_spec:
        target = tasks[external_spec.get("affected_index", 1) - 1]
        externals = (
            ExternalDependencySnapshot(
                id=ExternalDependencyId(UUID(int=300)),
                workspace_id=target.workspace_id,
                deliverable="외부 결과물",
                owner_label="민수",
                expected_delivery_at=DEADLINE
                + timedelta(hours=external_spec["delivery_offset_hours"]),
                uncertainty_buffer_minutes=external_spec.get("buffer_minutes", 60),
                fallback_available=external_spec.get("fallback", False),
                fallback_task_ids=(),
                affected_task_ids=(target.id,),
                version=1,
            ),
        )

    date_only = spec.get("date_only_deadline", False)
    milestone = MilestoneSnapshot(
        id=MILESTONE_ID,
        workspace_id=WORKSPACE,
        workstream_id=WORKSTREAM,
        title="제출",
        deadline_date=DEADLINE.date(),
        deadline_at=None if date_only else DEADLINE,
        deadline_date_known=True,
        deadline_time_known=not date_only,
        deadline_type=DeadlineType.HARD_DEADLINE,
        required_buffer_minutes=spec.get("buffer_minutes", 30),
        version=1,
    )

    availability_hours = spec.get("availability_hours", 6.25)
    window_start = NOW + timedelta(hours=spec.get("window_offset_hours", 0))
    windows = (
        (
            AvailabilityWindow(
                start_at=window_start,
                end_at=window_start + timedelta(hours=availability_hours),
                tags=frozenset({"focus"}),
            ),
        )
        if availability_hours
        else ()
    )

    pinned = frozenset(TaskId(UUID(int=value)) for value in spec.get("pinned", []))

    prior = None
    if spec.get("prior_first_minutes"):
        start = NOW + timedelta(hours=spec.get("prior_start_offset_hours", 0))
        prior = PriorPlanSnapshot(
            id=UUID(int=900),
            input_hash="prior",
            allocations=(
                PriorAllocation(
                    task_id=TaskId(UUID(int=1)),
                    start_at=start,
                    end_at=start + timedelta(minutes=spec["prior_first_minutes"]),
                ),
            ),
        )

    return PlannerInput(
        planner_version="planner-spec-1.0",
        now_utc=NOW,
        user_timezone="Asia/Seoul",
        horizon_end_utc=DEADLINE + timedelta(days=2),
        slot_minutes=15,
        availability_windows=windows,
        calendar_events=(),
        tasks=tasks,
        milestones=(milestone,),
        task_dependencies=dependencies,
        external_dependencies=externals,
        pinned_task_ids=pinned,
        excluded_dates=(),
        prior_plan_snapshot=prior,
    )


__all__ = ["build_vector_input"]
