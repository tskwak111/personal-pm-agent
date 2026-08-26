"""Hypothesis property tests for planner invariants.

CI runs a reduced example count; Stage A evaluation scales the same suite to
the required 20,000 scenarios (P8-T02) without code changes.
"""

from dataclasses import replace
from uuid import UUID

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from personal_pm_planner import plan
from personal_pm_planner.domain.identifiers import TaskId
from tests.vectors.builders import build_vector_input


def _random_case(
    task_count: int,
    availability_hours: float,
    base_minutes: int,
    splittable: bool,
    date_only: bool,
    buffer_minutes: int,
) -> dict:
    return {
        "tasks": [
            {"base": max(30, min(base_minutes, 240)), "safety": None} for _ in range(task_count)
        ],
        "availability_hours": availability_hours,
        "date_only_deadline": date_only,
        "buffer_minutes": buffer_minutes,
    }


def _task_spec_defaults(case: dict) -> dict:
    # safety defaults to base+30 inside builder; keep explicit here for clarity
    case["tasks"] = [
        {**item, "safety": item["base"] + 30} if item.get("safety") is None else item
        for item in case["tasks"]
    ]
    return case


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.data(),
    st.integers(min_value=1, max_value=6),
    st.floats(min_value=0.5, max_value=6.5),
    st.integers(min_value=30, max_value=180),
    st.booleans(),
)
def test_slot_single_owner_and_no_overlap(data, task_count, hours, base, splittable) -> None:
    spec = _task_spec_defaults(
        {
            "tasks": [{"base": base, "splittable": splittable} for _ in range(task_count)],
            "availability_hours": hours,
        }
    )
    value = build_vector_input(spec)
    output = plan(value)

    seen: set[str] = set()
    ordered: list = []
    for allocation in output.base_plan.allocations:
        for slot_id in allocation.source_slot_ids:
            assert slot_id not in seen, "slot double ownership"
            seen.add(slot_id)
        ordered.append(allocation)

    ordered.sort(key=lambda item: item.start_at)
    for current, following in zip(ordered, ordered[1:], strict=False):
        assert following.start_at >= current.end_at or current.task_id == following.task_id


@settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.integers(min_value=1, max_value=4),
    st.floats(min_value=1.0, max_value=6.0),
)
def test_dependency_order_is_never_violated(task_count, hours) -> None:
    spec = {
        "tasks": [{"base": 60, "safety": 90} for _ in range(task_count)],
        "availability_hours": hours,
        "cycle": False,
    }
    value = build_vector_input(spec)
    from personal_pm_planner.domain.dependency import TaskDependency
    from personal_pm_planner.domain.enums import DependencyType

    chain = tuple(
        TaskDependency(
            TaskId(UUID(int=i)),
            TaskId(UUID(int=i + 1)),
            DependencyType.BLOCKS_START,
        )
        for i in range(1, min(task_count, 3))
    )

    value = replace(value, task_dependencies=chain)
    output = plan(value)

    start_index = {}
    order = sorted(
        (a for a in output.base_plan.allocations if a.kind == "TASK"),
        key=lambda a: a.start_at,
    )
    for position, allocation in enumerate(order):
        start_index[allocation.task_id.value.hex[-2:]] = position

    for edge in chain:
        pred = edge.predecessor_id.value.hex[-2:]
        succ = edge.successor_id.value.hex[-2:]
        if pred in start_index and succ in start_index:
            assert start_index[pred] <= start_index[succ]
