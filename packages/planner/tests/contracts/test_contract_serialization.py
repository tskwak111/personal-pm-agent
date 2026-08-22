from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from personal_pm_planner import PlannerInput
from personal_pm_planner.contracts.input import canonical_input_bytes, input_hash
from personal_pm_planner.domain.availability import AvailabilityWindow
from personal_pm_planner.domain.dependency import TaskDependency
from personal_pm_planner.domain.enums import (
    DeadlineType,
    DependencyType,
    TaskStatus,
)
from personal_pm_planner.domain.identifiers import (
    MilestoneId,
    TaskId,
    WorkspaceId,
    WorkstreamId,
)
from personal_pm_planner.domain.task import TaskSnapshot
from personal_pm_planner.domain.work import MilestoneSnapshot

WORKSPACE = WorkspaceId(UUID("00000000-0000-0000-0000-000000000001"))
NOW = datetime(2026, 8, 23, 3, 0, tzinfo=UTC)


def make_task(offset: int) -> TaskSnapshot:
    return TaskSnapshot(
        id=TaskId(UUID(int=offset)),
        workspace_id=WORKSPACE,
        workstream_id=WorkstreamId(UUID(int=100)),
        milestone_id=MilestoneId(UUID(int=200)),
        title=f"task-{offset}",
        status=TaskStatus.READY,
        deadline_date=date(2026, 9, 10),
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
        pinned=False,
        waiting_reason=None,
        version=1,
    )


@pytest.fixture
def planner_input_factory():
    def factory(*, reverse_tasks: bool = False, extra_dependency: bool = False) -> PlannerInput:
        tasks = [make_task(offset) for offset in range(1, 6)]
        if reverse_tasks:
            tasks.reverse()
        dependencies = [
            TaskDependency(
                TaskId(UUID(int=1)),
                TaskId(UUID(int=2)),
                DependencyType.BLOCKS_START,
            )
        ]
        return PlannerInput(
            planner_version="planner-spec-1.0",
            now_utc=NOW,
            user_timezone="Asia/Seoul",
            horizon_end_utc=NOW + timedelta(days=14),
            slot_minutes=15,
            availability_windows=(
                AvailabilityWindow(
                    start_at=NOW,
                    end_at=NOW + timedelta(hours=4),
                    tags=frozenset({"focus"}),
                ),
            ),
            calendar_events=(),
            tasks=tuple(tasks),
            milestones=(
                MilestoneSnapshot(
                    id=MilestoneId(UUID(int=200)),
                    workspace_id=WORKSPACE,
                    workstream_id=WorkstreamId(UUID(int=100)),
                    title="제출",
                    deadline_date=date(2026, 9, 10),
                    deadline_at=None,
                    deadline_date_known=True,
                    deadline_time_known=False,
                    deadline_type=DeadlineType.HARD_DEADLINE,
                    required_buffer_minutes=60,
                    version=1,
                ),
            ),
            task_dependencies=tuple(dependencies),
            external_dependencies=(),
            pinned_task_ids=frozenset(),
            excluded_dates=(),
        )

    return factory


def test_canonical_input_is_independent_of_collection_order(planner_input_factory) -> None:
    first = planner_input_factory(reverse_tasks=False)
    second = planner_input_factory(reverse_tasks=True)
    assert canonical_input_bytes(first) == canonical_input_bytes(second)


def test_input_hash_is_stable_and_hex(planner_input_factory) -> None:
    digest = input_hash(planner_input_factory())
    assert len(digest) == 64
    again = input_hash(planner_input_factory())
    assert digest == again


def test_naive_now_is_rejected(planner_input_factory) -> None:
    value = planner_input_factory()
    object.__setattr__(value, "now_utc", NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="timezone-aware"):
        canonical_input_bytes(value)


def test_uuid_fields_never_leak_into_canonical_bytes(planner_input_factory) -> None:
    payload = canonical_input_bytes(planner_input_factory()).decode("utf-8")
    assert str(uuid4()) not in payload or "task-" in payload
