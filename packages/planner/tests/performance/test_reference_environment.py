"""Reference-environment performance smoke (full bench is the Stage A report)."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import uuid4

from personal_pm_planner.domain.enums import TaskStatus, Uncertainty
from personal_pm_planner.domain.identifiers import TaskId, WorkspaceId, WorkstreamId
from personal_pm_planner.domain.task import TaskSnapshot


def _make_tasks(n: int) -> list[TaskSnapshot]:
    ws = WorkspaceId(uuid4())
    wsn = WorkstreamId(uuid4())
    return [
        TaskSnapshot(
            id=TaskId(uuid4()),
            workspace_id=ws,
            workstream_id=wsn,
            milestone_id=None,
            title=f"t{i}",
            status=TaskStatus.READY,
            deadline_date=None,
            deadline_at=None,
            deadline_time_known=False,
            start_after=None,
            base_duration_minutes=60,
            safety_duration_minutes=90,
            remaining_base_minutes=60,
            remaining_safety_minutes=90,
            uncertainty=Uncertainty.MEDIUM,
            splittable=True,
            min_chunk_minutes=30,
            pinned=False,
            waiting_reason=None,
            version=1,
        )
        for i in range(n)
    ]


def test_60_tasks_plan_under_two_seconds() -> None:
    from personal_pm_planner.contracts.input import PlannerInput
    from personal_pm_planner.planner import plan

    now = datetime.now(UTC)
    inp = PlannerInput(
        planner_version="planner-spec-1.0",
        now_utc=now,
        user_timezone="Asia/Seoul",
        horizon_end_utc=now + __import__("datetime").timedelta(days=7),
        slot_minutes=15,
        availability_windows=(),
        calendar_events=(),
        tasks=tuple(_make_tasks(60)),
        milestones=(),
        task_dependencies=(),
        external_dependencies=(),
        pinned_task_ids=frozenset(),
        excluded_dates=(),
    )
    started = time.monotonic()
    plan(inp)
    elapsed = time.monotonic() - started
    assert elapsed < 2.0
