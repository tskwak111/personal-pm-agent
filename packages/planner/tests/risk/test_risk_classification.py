from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from personal_pm_planner.contracts.input import PlannerInput
from personal_pm_planner.domain.availability import AvailabilityWindow, ExternalDependencySnapshot
from personal_pm_planner.domain.dependency import TaskDependency
from personal_pm_planner.domain.enums import DependencyType
from personal_pm_planner.domain.identifiers import ExternalDependencyId, TaskId

from tests.conftest import MILESTONE, make_milestone, make_task

NOW = datetime(2026, 9, 1, 0, 30, tzinfo=UTC)  # inside one Seoul day
DEADLINE = datetime(2026, 9, 10, 3, 0, tzinfo=UTC)


def build_case(*, task_specs, buffer_minutes=0, deadline_time_known=True, deadline=None):
    window = AvailabilityWindow(
        start_at=NOW,
        end_at=NOW + timedelta(hours=6.25),
        tags=frozenset({"focus"}),
    )
    milestone_deadline = deadline if deadline is not None else DEADLINE
    return PlannerInput(
        planner_version="planner-spec-1.0",
        now_utc=NOW,
        user_timezone="Asia/Seoul",
        horizon_end_utc=milestone_deadline + timedelta(days=2),
        slot_minutes=15,
        availability_windows=(window,),
        calendar_events=(),
        tasks=tuple(make_task(offset, **spec) for offset, spec in enumerate(task_specs, start=1)),
        milestones=(
            make_milestone(
                deadline_date=None if deadline_time_known else milestone_deadline.date(),
                deadline_at=milestone_deadline if deadline_time_known else None,
                deadline_date_known=not deadline_time_known,
                deadline_time_known=deadline_time_known,
                required_buffer_minutes=buffer_minutes,
            ),
        ),
        task_dependencies=(),
        external_dependencies=(),
        pinned_task_ids=frozenset(),
        excluded_dates=(),
    )


def passes_for(value):
    from personal_pm_planner.scheduling.passes import run_planning_passes

    return run_planning_passes(value)


def risks_for(value):
    from personal_pm_planner.risk.classify import build_risk_context, calculate_risks

    passes = passes_for(value)
    context = build_risk_context(value)
    return calculate_risks(passes, context), passes


def test_base_possible_safety_impossible_is_high() -> None:
    value = build_case(
        task_specs=[
            {"base": 120, "safety": 180},
            {"base": 120, "safety": 180},
        ]
    )
    risks, _ = risks_for(value)
    risk = risks[MILESTONE]
    assert risk.base_coverage == pytest.approx(1.0)
    assert risk.safety_coverage < 1.0
    assert risk.risk_level == "HIGH"
    assert "SAFETY_COVERAGE_BELOW_ONE" in risk.reasons


def test_capacity_critical_when_base_infeasible() -> None:
    value = build_case(
        task_specs=[
            {"base": 200, "safety": 240},
            {"base": 200, "safety": 240},
        ],
        buffer_minutes=60,
    )
    risks, _ = risks_for(value)
    assert risks[MILESTONE].risk_level == "CRITICAL"
    assert any("BASE_COVERAGE" in reason for reason in risks[MILESTONE].reasons)


def test_date_only_current_deadline_remains_unknown() -> None:
    value = build_case(
        task_specs=[{"base": 120, "safety": 180}],
        deadline_time_known=False,
    )
    risks, _ = risks_for(value)
    assert risks[MILESTONE].risk_level == "UNKNOWN"


def test_low_when_everything_fits_with_slack() -> None:
    value = build_case(task_specs=[{"base": 60, "safety": 75}], buffer_minutes=30)
    risks, _ = risks_for(value)
    risk = risks[MILESTONE]
    assert risk.base_coverage == pytest.approx(1.0)
    assert risk.safety_coverage == pytest.approx(1.0)
    assert risk.risk_level == "LOW"


def test_external_dependency_late_delivery_is_high() -> None:
    from personal_pm_planner.graph.build import build_graph_analysis
    from personal_pm_planner.risk.external import assess_external_dependencies

    task = make_task(1, base=90, safety=120)
    t1 = task.id
    external = ExternalDependencySnapshot(
        id=ExternalDependencyId(UUID(int=300)),
        workspace_id=task.workspace_id,
        deliverable="데이터셋",
        owner_label="민수",
        expected_delivery_at=DEADLINE - timedelta(hours=12),
        uncertainty_buffer_minutes=60,
        fallback_available=False,
        fallback_task_ids=(),
        affected_task_ids=(t1,),
        version=1,
    )
    value = build_case(task_specs=[{}])
    value = PlannerInput(
        planner_version=value.planner_version,
        now_utc=value.now_utc,
        user_timezone=value.user_timezone,
        horizon_end_utc=value.horizon_end_utc,
        slot_minutes=value.slot_minutes,
        availability_windows=value.availability_windows,
        calendar_events=value.calendar_events,
        tasks=(task,),
        milestones=value.milestones,
        task_dependencies=(
            # keep dependency shape valid: no edges needed here
        ),
        external_dependencies=(external,),
        pinned_task_ids=frozenset(),
        excluded_dates=(),
    )
    analysis = build_graph_analysis(value)
    assessments = assess_external_dependencies(value, analysis)
    assert len(assessments) == 1
    # Delivery (D-12h) is later than latest safe handoff (D-2h safety) -> HIGH
    assert assessments[0].risk_level == "HIGH"


def test_cycle_blocks_required_path_into_critical() -> None:
    from personal_pm_planner.risk.classify import build_risk_context, calculate_risks

    a, b = TaskId(UUID(int=1)), TaskId(UUID(int=2))
    base_value = build_case(task_specs=[{"base": 60, "safety": 90}, {"base": 60, "safety": 90}])
    value = PlannerInput(
        planner_version=base_value.planner_version,
        now_utc=base_value.now_utc,
        user_timezone=base_value.user_timezone,
        horizon_end_utc=base_value.horizon_end_utc,
        slot_minutes=base_value.slot_minutes,
        availability_windows=base_value.availability_windows,
        calendar_events=base_value.calendar_events,
        tasks=base_value.tasks,
        milestones=base_value.milestones,
        task_dependencies=(
            TaskDependency(a, b, DependencyType.BLOCKS_START),
            TaskDependency(b, a, DependencyType.BLOCKS_START),
        ),
        external_dependencies=(),
        pinned_task_ids=frozenset(),
        excluded_dates=(),
    )
    passes = passes_for(value)
    context = build_risk_context(value)
    risks = calculate_risks(passes, context)
    assert risks[MILESTONE].risk_level == "CRITICAL"
    assert "DEPENDENCY_CYCLE_BLOCKS_REQUIRED_PATH" in risks[MILESTONE].reasons
