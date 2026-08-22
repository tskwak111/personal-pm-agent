from dataclasses import FrozenInstanceError
from datetime import date
from uuid import UUID

import pytest
from personal_pm_planner.domain.enums import TaskStatus
from personal_pm_planner.domain.identifiers import (
    MilestoneId,
    TaskId,
    WorkspaceId,
    WorkstreamId,
)

WORKSPACE = WorkspaceId(UUID("00000000-0000-0000-0000-000000000001"))
WORKSTREAM = WorkstreamId(UUID("00000000-0000-0000-0000-000000000003"))


@pytest.fixture
def task_factory():
    def factory(**overrides: object):
        from personal_pm_planner.domain.task import TaskSnapshot

        defaults: dict[str, object] = {
            "id": TaskId(UUID("00000000-0000-0000-0000-00000000000a")),
            "workspace_id": WORKSPACE,
            "workstream_id": WORKSTREAM,
            "milestone_id": MilestoneId(UUID("00000000-0000-0000-0000-000000000002")),
            "title": "ERD 작성",
            "status": TaskStatus.READY,
            "deadline_date": date(2026, 9, 10),
            "deadline_at": None,
            "deadline_time_known": False,
            "start_after": None,
            "base_duration_minutes": 60,
            "safety_duration_minutes": 90,
            "remaining_base_minutes": 60,
            "remaining_safety_minutes": 90,
            "uncertainty": "medium",
            "splittable": True,
            "min_chunk_minutes": 30,
            "pinned": False,
            "waiting_reason": None,
            "version": 1,
        }
        defaults.update(overrides)
        return TaskSnapshot(**defaults)  # type: ignore[arg-type]

    return factory


def test_task_snapshot_is_immutable_and_validated(task_factory) -> None:
    task = task_factory()
    assert task.workspace_id == WORKSPACE
    with pytest.raises(FrozenInstanceError):
        task.status = TaskStatus.DONE  # type: ignore[misc]


def test_base_duration_must_be_positive(task_factory) -> None:
    with pytest.raises(ValueError, match="base_duration_minutes"):
        task_factory(base_duration_minutes=0)


def test_safety_duration_cannot_be_below_base(task_factory) -> None:
    with pytest.raises(ValueError, match="safety_duration"):
        task_factory(base_duration_minutes=120, safety_duration_minutes=90)


def test_done_or_cancelled_tasks_have_no_remaining_work(task_factory) -> None:
    with pytest.raises(ValueError, match="remaining"):
        task_factory(status=TaskStatus.DONE, remaining_base_minutes=30)


def test_waiting_task_cannot_become_ready_while_external_wait_remains(task_factory) -> None:
    task = task_factory(status=TaskStatus.WAITING, waiting_reason="external:dataset")
    from personal_pm_planner.domain.state_machine import transition_task

    with pytest.raises(ValueError, match="waiting condition"):
        transition_task(task, TaskStatus.READY, waiting_resolved=False)


def test_done_requires_zero_remaining_minutes(task_factory) -> None:
    task = task_factory(status=TaskStatus.IN_PROGRESS, remaining_base_minutes=30)
    from personal_pm_planner.domain.state_machine import transition_task

    with pytest.raises(ValueError, match="remaining"):
        transition_task(task, TaskStatus.DONE, completion_confirmed=True)


def test_done_requires_user_confirmation(task_factory) -> None:
    task = task_factory(
        status=TaskStatus.IN_PROGRESS,
        remaining_base_minutes=0,
        remaining_safety_minutes=0,
    )
    from personal_pm_planner.domain.state_machine import transition_task

    with pytest.raises(ValueError, match="completion confirmation"):
        transition_task(task, TaskStatus.DONE)


def test_allowed_transition_returns_new_snapshot_with_bumped_version(task_factory) -> None:
    from personal_pm_planner.domain.state_machine import transition_task

    task = task_factory(status=TaskStatus.PLANNED)
    ready = transition_task(task, TaskStatus.READY)
    assert ready.status is TaskStatus.READY
    assert ready.version == task.version + 1
    assert task.status is TaskStatus.PLANNED


def test_forbidden_transition_is_rejected(task_factory) -> None:
    from personal_pm_planner.domain.state_machine import transition_task

    task = task_factory(status=TaskStatus.DRAFT)
    with pytest.raises(ValueError, match="not allowed"):
        transition_task(task, TaskStatus.IN_PROGRESS)


@pytest.mark.parametrize("source", list(TaskStatus))
def test_every_transition_edge_is_classified(source, task_factory) -> None:
    from personal_pm_planner.domain.state_machine import ALLOWED_TRANSITIONS, transition_task

    for target in TaskStatus:
        frozen = source in (TaskStatus.DONE, TaskStatus.CANCELLED)
        zero_remaining = target is TaskStatus.DONE or frozen
        task = task_factory(
            status=source,
            waiting_reason="external:dataset" if source is TaskStatus.WAITING else None,
            remaining_base_minutes=0 if zero_remaining else 60,
            remaining_safety_minutes=0 if zero_remaining else 90,
        )
        kwargs: dict[str, object] = {
            "waiting_resolved": True,
            "blocker_resolved": True,
            "completion_confirmed": True,
            "waiting_reason": "external:review",
        }
        allowed = target in ALLOWED_TRANSITIONS[source]
        if allowed:
            moved = transition_task(task, target, **kwargs)
            assert moved.status is target
            assert moved.version == task.version + 1
            # Leaving Waiting resolves the reason; entering it requires one.
            expected_reason = (
                "external:review"
                if target is TaskStatus.WAITING and source is not TaskStatus.WAITING
                else None
            )
            assert moved.waiting_reason == expected_reason
        else:
            with pytest.raises(ValueError, match="not allowed"):
                transition_task(task, target, **kwargs)


def test_ready_task_can_enter_waiting_with_reason(task_factory) -> None:
    from personal_pm_planner.domain.state_machine import transition_task

    task = task_factory(status=TaskStatus.READY)
    waiting = transition_task(task, TaskStatus.WAITING, waiting_reason="external:data")
    assert waiting.waiting_reason == "external:data"


def test_entering_waiting_without_reason_is_rejected(task_factory) -> None:
    from personal_pm_planner.domain.state_machine import transition_task

    task = task_factory(status=TaskStatus.READY)
    with pytest.raises(ValueError, match="waiting reason"):
        transition_task(task, TaskStatus.WAITING)
