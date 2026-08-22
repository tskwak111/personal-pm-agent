from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from personal_pm_planner.availability.slots import AvailabilityContext, build_unique_slots
from personal_pm_planner.domain.availability import AvailabilityWindow
from personal_pm_planner.domain.enums import ImportanceLevel
from personal_pm_planner.domain.identifiers import TaskId
from personal_pm_planner.scheduling.priority import PriorityClass, SchedulableTask

DAY_START = datetime(2026, 8, 23, 9, 0, tzinfo=UTC)


def make_window(hours: float):
    from personal_pm_planner.domain.availability import AvailabilityWindow

    return AvailabilityWindow(
        start_at=DAY_START,
        end_at=DAY_START + timedelta(hours=hours),
        tags=frozenset({"focus"}),
    )


def make_schedulable(value: int, **overrides) -> SchedulableTask:
    defaults = {
        "id": TaskId(UUID(int=value)),
        "priority_class": PriorityClass.P1,
        "must_start_by_at": None,
        "effective_deadline_at": None,
        "critical_path_unlock_count": 0,
        "external_commitment": False,
        "user_importance": ImportanceLevel.NORMAL,
        "prior_plan_position": None,
        "context_switch_penalty": 1,
        "created_at": datetime(2026, 8, 20, tzinfo=UTC),
        "base_duration_minutes": 240,
        "safety_duration_minutes": 240,
    }
    defaults.update(overrides)
    return SchedulableTask(**defaults)


@pytest.fixture
def tv01_case():
    """TV-01: two P1 tasks each need the whole shared 4h capacity."""
    slots = build_unique_slots(
        AvailabilityContext(availability_windows=(make_window(4),), capacity_factor=1.0)
    )
    tasks = (
        make_schedulable(1),
        make_schedulable(2),
    )
    return {
        "arguments": {
            "tasks": tasks,
            "slots": slots,
            "duration_field": "base_duration_minutes",
            "pass_type": "base",
        },
        "task_ids": {task.id for task in tasks},
    }


@pytest.fixture
def tv08_case():
    """TV-08: non-splittable 90min cannot fit 45min free runs."""
    from personal_pm_planner.domain.availability import AvailabilityWindow

    morning = AvailabilityWindow(
        start_at=DAY_START,
        end_at=DAY_START + timedelta(minutes=45),
        tags=frozenset({"focus"}),
    )
    afternoon = AvailabilityWindow(
        start_at=DAY_START + timedelta(minutes=90),
        end_at=DAY_START + timedelta(minutes=135),
        tags=frozenset({"focus"}),
    )
    slots = build_unique_slots(
        AvailabilityContext(
            availability_windows=(morning, afternoon),
            capacity_factor=1.0,
        )
    )
    task = make_schedulable(9, base_duration_minutes=90, splittable=False)
    return {
        "arguments": {
            "tasks": (task,),
            "slots": slots,
            "duration_field": "base_duration_minutes",
            "pass_type": "base",
        },
        "task_id": task.id,
    }


def test_shared_capacity_is_never_double_allocated(tv01_case) -> None:
    from personal_pm_planner.scheduling.serial import serial_schedule

    result = serial_schedule(**tv01_case["arguments"])
    allocated_slot_ids = [
        slot_id for item in result.allocations for slot_id in item.source_slot_ids
    ]
    assert len(allocated_slot_ids) == len(set(allocated_slot_ids))
    assert result.total_allocated_minutes == 240
    placed = {item.task_id for item in result.allocations}
    unplaced = tv01_case["task_ids"] - placed
    assert len(unplaced) == 1
    assert unplaced <= set(result.unallocated_task_ids)


def test_non_splittable_task_requires_contiguous_capacity(tv08_case) -> None:
    from personal_pm_planner.scheduling.serial import serial_schedule

    result = serial_schedule(**tv08_case["arguments"])
    assert tv08_case["task_id"] in result.unallocated_task_ids
    assert result.total_allocated_minutes == 0


def test_splittable_task_fills_runs_with_minimum_chunks() -> None:
    from personal_pm_planner.scheduling.serial import serial_schedule

    morning = make_window(1.25)  # 75 minutes
    afternoon = AvailabilityWindow(
        start_at=DAY_START + timedelta(hours=2),
        end_at=DAY_START + timedelta(hours=3, minutes=15),
        tags=frozenset({"focus"}),
    )
    slots = build_unique_slots(
        AvailabilityContext(availability_windows=(morning, afternoon), capacity_factor=1.0)
    )
    task = make_schedulable(5, base_duration_minutes=120)
    result = serial_schedule(
        tasks=(task,),
        slots=slots,
        duration_field="base_duration_minutes",
        pass_type="base",
    )
    chunks = sorted(result.allocations, key=lambda item: item.start_at)
    assert len(chunks) == 2
    assert all(chunk.end_at - chunk.start_at >= timedelta(minutes=30) for chunk in chunks)
    assert [item.chunk_index for item in chunks] == [0, 1]
    assert result.total_allocated_minutes == 120


def test_respects_start_after_constraint() -> None:
    from personal_pm_planner.scheduling.serial import serial_schedule

    slots = build_unique_slots(
        AvailabilityContext(availability_windows=(make_window(4),), capacity_factor=1.0)
    )
    task = make_schedulable(
        7,
        base_duration_minutes=60,
        start_after=DAY_START + timedelta(hours=2),
    )
    result = serial_schedule(
        tasks=(task,),
        slots=slots,
        duration_field="base_duration_minutes",
        pass_type="base",
    )
    first_start = min(item.start_at for item in result.allocations)
    assert first_start >= DAY_START + timedelta(hours=2)
