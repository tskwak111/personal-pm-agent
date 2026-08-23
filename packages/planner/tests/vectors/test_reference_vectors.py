import json
from pathlib import Path

import pytest
from personal_pm_planner import plan
from personal_pm_planner.replanning.optimize import replan

from tests.vectors.builders import build_vector_input

VECTOR_DIR = Path("evals/planner-vectors/reference")


def load_vectors():
    return sorted(VECTOR_DIR.glob("tv-*.json"))


def base_allocated_minutes(output) -> int:
    total = 0
    for allocation in output.base_plan.allocations if output.base_plan else ():
        if allocation.kind != "TASK":
            continue
        total += int((allocation.end_at - allocation.start_at).total_seconds() // 60)
    return total


def unallocated_task_ids(output, spec_input) -> set:
    placed = {
        allocation.task_id
        for allocation in output.base_plan.allocations
        if allocation.kind == "TASK"
    }
    return {task.id for task in spec_input.tasks} - placed


def first_risk_level(output):
    assert output.milestone_risks, "expected milestone risks"
    return output.milestone_risks[0].risk_level


@pytest.mark.parametrize("vector_path", load_vectors(), ids=lambda p: p.stem)
def test_reference_vector_matches_expected(vector_path) -> None:
    vector = json.loads(vector_path.read_text(encoding="utf-8"))
    value = build_vector_input(vector["input"])
    output = plan(value)
    expected = vector["expected"]

    if "risk_level" in expected:
        assert first_risk_level(output) == expected["risk_level"]
    if "risk_level_not_in" in expected:
        assert first_risk_level(output) not in expected["risk_level_not_in"]
    if "base_allocated_minutes" in expected:
        assert base_allocated_minutes(output) == expected["base_allocated_minutes"]
    if "min_unallocated_tasks" in expected:
        assert len(unallocated_task_ids(output, value)) >= expected["min_unallocated_tasks"]
    if "unallocated_task_count_min" in expected:
        assert len(unallocated_task_ids(output, value)) >= expected["unallocated_task_count_min"]
    if "warning_contains" in expected:
        all_warnings = [*output.validation_warnings, *output.external_warnings]
        assert any(expected["warning_contains"] in warning for warning in all_warnings), (
            output.validation_warnings,
            output.external_warnings,
        )
    if expected.get("warning_or_risk_higher_than_low"):
        higher = any(
            level in (*output.validation_warnings, *output.external_warnings)
            or "EXTERNAL_RISK_HIGH" in str(output.external_warnings)
            for level in ("HIGH", "CRITICAL")
        )
        assert higher or first_risk_level(output) in ("HIGH", "CRITICAL", "MEDIUM")
    if "changed_task_count" in expected:
        outcome = replan(value)
        assert outcome.diff.changed_task_count == expected["changed_task_count"]
    if expected.get("critical_before_gt_after"):
        outcome = replan(value)
        assert outcome.after.critical_milestones < outcome.before.critical_milestones


def test_tv02_repeated_execution_is_identical() -> None:
    vector = json.loads((VECTOR_DIR / "tv-02.json").read_text(encoding="utf-8"))
    value = build_vector_input(vector["input"])
    cores = [json.dumps(plan(value).canonical_core(), sort_keys=True) for _ in range(20)]
    assert len(set(cores)) == 1


def test_tv04_date_only_deadline_fact_untouched() -> None:
    vector = json.loads((VECTOR_DIR / "tv-04.json").read_text(encoding="utf-8"))
    value = build_vector_input(vector["input"])
    assert value.milestones[0].deadline_time_known is False
    assert value.milestones[0].deadline_at is None
    output = plan(value)
    assert output.status == "OK"


def test_invalid_input_preserves_status_and_never_ok() -> None:
    from personal_pm_planner.domain.enums import TaskStatus

    value = build_vector_input({"tasks": [{"base": 60, "safety": 75}], "availability_hours": 4})
    corrupted = value.tasks[0]
    object.__setattr__(corrupted, "status", TaskStatus.DONE)
    object.__setattr__(corrupted, "remaining_base_minutes", 30)
    broken = type(value)(
        planner_version=value.planner_version,
        now_utc=value.now_utc,
        user_timezone=value.user_timezone,
        horizon_end_utc=value.horizon_end_utc,
        slot_minutes=value.slot_minutes,
        availability_windows=value.availability_windows,
        calendar_events=value.calendar_events,
        tasks=(corrupted,) + value.tasks[1:],
        milestones=value.milestones,
        task_dependencies=value.task_dependencies,
        external_dependencies=value.external_dependencies,
        pinned_task_ids=value.pinned_task_ids,
        excluded_dates=value.excluded_dates,
        prior_plan_snapshot=value.prior_plan_snapshot,
    )
    output = plan(broken)
    assert output.status == "INVALID_INPUT"
    assert output.base_plan is None
