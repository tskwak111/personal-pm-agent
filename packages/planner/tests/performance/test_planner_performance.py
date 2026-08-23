"""Light performance smoke inside unit time budget.

The full reference benchmark (500 tasks / 42 days / 15-minute slots, P95
thresholds) runs as Stage A evidence in P8-T02; this smoke keeps a regression
tripwire in every commit.
"""

import time

from personal_pm_planner import plan

from tests.vectors.builders import build_vector_input


def test_moderate_case_plans_within_two_seconds() -> None:
    spec = {
        "tasks": [{"base": 60, "safety": 90} for _ in range(60)],
        "availability_hours": 8,
    }
    value = build_vector_input(spec)
    started = time.perf_counter()
    output = plan(value)
    elapsed = time.perf_counter() - started
    assert output.status == "OK"
    assert elapsed < 2.0, f"plan() took {elapsed:.2f}s for 60 tasks"


def test_repeated_plan_is_byte_stable() -> None:
    value = build_vector_input(
        {"tasks": [{"base": 60, "safety": 75} for _ in range(10)], "availability_hours": 6}
    )
    first = plan(value)
    second = plan(value)
    assert first.canonical_core() == second.canonical_core()
