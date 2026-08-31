"""Stage A property scenarios: generated inputs against hard invariants."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from personal_pm_planner import plan
from personal_pm_planner.domain.enums import TaskStatus, Uncertainty
from personal_pm_planner.domain.identifiers import TaskId, WorkstreamId
from personal_pm_planner.domain.task import TaskSnapshot
from tests.vectors.builders import build_vector_input

GENERATED_NODE = (
    "packages/planner/tests/properties/test_generated_scenarios.py::"
    "test_generated_plans_obey_capacity_and_determinism"
)
GENERATED_GATES = ("PLAN-001", "PLAN-004", "PLAN-006")


def _scenario_count() -> int:
    return int(os.environ.get("STAGE_A_SCENARIOS", "25"))


def _task(i: int, remaining_base: int, status: str) -> TaskSnapshot:
    return TaskSnapshot(
        id=TaskId(_uuid_from_int(i)),
        workspace_id=WorkstreamId(_uuid_from_int(999)),
        workstream_id=WorkstreamId(_uuid_from_int(999)),
        milestone_id=None,
        title=f"task-{i}",
        status=TaskStatus(status),
        deadline_date=None,
        deadline_at=None,
        deadline_time_known=False,
        start_after=None,
        base_duration_minutes=max(1, remaining_base),
        safety_duration_minutes=max(1, remaining_base) + 30,
        remaining_base_minutes=remaining_base,
        remaining_safety_minutes=remaining_base + 30,
        uncertainty=Uncertainty("medium"),
        splittable=True,
        min_chunk_minutes=30,
        pinned=False,
        waiting_reason=None,
        version=1,
    )


def _uuid_from_int(i: int) -> object:
    import uuid

    return uuid.UUID(int=i % (2**128))


@given(
    st.integers(min_value=1, max_value=8),
    st.floats(min_value=0.5, max_value=8.0, allow_nan=False, allow_infinity=False),
    st.integers(min_value=30, max_value=240),
    st.booleans(),
)
@settings(
    max_examples=_scenario_count(),
    derandomize=True,
    database=None,
    deadline=None,
    suppress_health_check=(HealthCheck.too_slow,),
)
def test_generated_plans_obey_capacity_and_determinism(
    task_count: int,
    availability_hours: float,
    base_minutes: int,
    splittable: bool,
) -> None:
    """PLAN-001/004/006 over exactly the Stage A requested examples."""
    base = max(30, min(base_minutes, 240))
    value = build_vector_input(
        {
            "tasks": [
                {"base": base, "safety": base + 30, "splittable": splittable}
                for _ in range(task_count)
            ],
            "availability_hours": availability_hours,
        }
    )
    first = plan(value)
    second = plan(value)
    assert first.canonical_core() == second.canonical_core()
    assert first.base_plan is not None

    slot_ids = [
        slot_id
        for allocation in first.base_plan.allocations
        for slot_id in allocation.source_slot_ids
    ]
    assert len(slot_ids) == len(set(slot_ids))
    allocated_minutes = sum(
        int((allocation.end_at - allocation.start_at).total_seconds() // 60)
        for allocation in first.base_plan.allocations
    )
    assert allocated_minutes <= int(availability_hours * 60)


def test_terminal_tasks_have_zero_remaining() -> None:
    """PLAN-001 invariant: done/cancelled implies zero remaining."""
    # The domain itself rejects terminal tasks with remaining minutes.
    import pytest as _pytest

    with _pytest.raises(ValueError):
        TaskSnapshot(
            id=TaskId(_uuid_from_int(1)),
            workspace_id=WorkstreamId(_uuid_from_int(999)),
            workstream_id=WorkstreamId(_uuid_from_int(999)),
            milestone_id=None,
            title="done-with-remaining",
            status=TaskStatus.DONE,
            deadline_date=None,
            deadline_at=None,
            deadline_time_known=False,
            start_after=None,
            base_duration_minutes=60,
            safety_duration_minutes=90,
            remaining_base_minutes=0,
            remaining_safety_minutes=30,
            uncertainty=Uncertainty("medium"),
            splittable=True,
            min_chunk_minutes=30,
            pinned=False,
            waiting_reason=None,
            version=1,
        )


def test_property_suite_smoke() -> None:
    tasks = [_task(i, 60, "ready") for i in range(3)]
    assert all(t.base_duration_minutes > 0 for t in tasks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Stage A scenarios")
    parser.add_argument("--scenarios", type=int, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.scenarios < 1:
        parser.error("--scenarios must be positive")

    environment = dict(os.environ)
    environment["STAGE_A_SCENARIOS"] = str(args.scenarios)
    result = subprocess.run(  # noqa: S603 - fixed interpreter and test node
        [sys.executable, "-m", "pytest", GENERATED_NODE, "-q"],
        capture_output=True,
        text=True,
        env=environment,
    )
    passed = result.returncode == 0
    payload = {
        "scenario_count": args.scenarios,
        "gates": {
            gate: {
                "executed": True,
                "checks": args.scenarios,
                "failures": 0 if passed else 1,
                "source": GENERATED_NODE,
            }
            for gate in GENERATED_GATES
        },
        "command": {
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
        },
    }
    args.observations.parent.mkdir(parents=True, exist_ok=True)
    args.observations.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
