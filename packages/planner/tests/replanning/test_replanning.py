from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from personal_pm_planner.contracts.input import (
    PlannerInput,
    PriorAllocation,
    PriorPlanSnapshot,
)
from personal_pm_planner.domain.enums import AuthorizationLevel
from personal_pm_planner.domain.identifiers import TaskId

from tests.conftest import make_milestone, make_task

NOW = datetime(2026, 9, 1, 0, 30, tzinfo=UTC)
DEADLINE = datetime(2026, 9, 10, 3, 0, tzinfo=UTC)


def build_value(*, task_specs, prior=None, pinned=frozenset()):
    from personal_pm_planner.domain.availability import AvailabilityWindow

    window = AvailabilityWindow(
        start_at=NOW,
        end_at=NOW + timedelta(hours=6.25),
        tags=frozenset({"focus"}),
    )
    return PlannerInput(
        planner_version="planner-spec-1.0",
        now_utc=NOW,
        user_timezone="Asia/Seoul",
        horizon_end_utc=DEADLINE + timedelta(days=2),
        slot_minutes=15,
        availability_windows=(window,),
        calendar_events=(),
        tasks=tuple(make_task(offset, **spec) for offset, spec in enumerate(task_specs, start=1)),
        milestones=(
            make_milestone(
                deadline_date=None,
                deadline_at=DEADLINE,
                deadline_date_known=False,
                deadline_time_known=True,
                required_buffer_minutes=30,
            ),
        ),
        task_dependencies=(),
        external_dependencies=(),
        pinned_task_ids=pinned,
        excluded_dates=(),
        prior_plan_snapshot=prior,
    )


def prior_snapshot(*, first_task_minutes: int) -> PriorPlanSnapshot:
    return PriorPlanSnapshot(
        id=UUID(int=900),
        input_hash="prior",
        allocations=(
            PriorAllocation(
                task_id=TaskId(UUID(int=1)),
                start_at=NOW,
                end_at=NOW + timedelta(minutes=first_task_minutes),
            ),
        ),
    )


def test_replanning_moves_only_one_task_when_that_resolves_risk() -> None:
    """Prior plan kept task 1 for only 60min; demand grew to 180.

    Keeping the prior shape leaves the milestone Critical. The minimal-change
    candidate extends/moves exactly that one task instead of reshaping all.
    """
    from personal_pm_planner.replanning.optimize import replan

    value = build_value(
        task_specs=[{"base": 260, "safety": 340}],
        prior=prior_snapshot(first_task_minutes=60),
    )
    outcome = replan(value)

    assert outcome.before.critical_milestones >= 1
    assert outcome.after.critical_milestones < outcome.before.critical_milestones
    # Only the one prior task participates in the diff.
    assert outcome.diff.changed_task_count == 1


def test_freeze_window_change_requires_proposal() -> None:
    # Prior placed task 1 three hours out; the fresh plan wants it earlier,
    # but the task is pinned, so only a proposal may move it.
    from datetime import datetime as _dt

    from personal_pm_planner.replanning.optimize import replan

    snapshot = PriorPlanSnapshot(
        id=UUID(int=900),
        input_hash="prior",
        allocations=(
            PriorAllocation(
                task_id=TaskId(UUID(int=1)),
                start_at=_dt(2026, 9, 1, 3, 30, tzinfo=UTC),
                end_at=_dt(2026, 9, 1, 5, 30, tzinfo=UTC),
            ),
        ),
    )
    value = build_value(
        task_specs=[{"base": 120, "safety": 150}],
        prior=snapshot,
        pinned={TaskId(UUID(int=1))},
    )
    outcome = replan(value)
    frozen_task = TaskId(UUID(int=1))
    assert frozen_task not in {move.task_id for move in outcome.applied_moves}
    assert any(
        proposal.approval_level is AuthorizationLevel.APPROVAL for proposal in outcome.proposals
    )


def test_public_plan_preserves_pinned_allocation_until_proposal_is_approved() -> None:
    from personal_pm_planner import plan

    snapshot = PriorPlanSnapshot(
        id=UUID(int=900),
        input_hash="prior",
        allocations=(
            PriorAllocation(
                task_id=TaskId(UUID(int=1)),
                start_at=datetime(2026, 9, 1, 3, 30, tzinfo=UTC),
                end_at=datetime(2026, 9, 1, 5, 30, tzinfo=UTC),
            ),
        ),
    )
    value = build_value(
        task_specs=[{"base": 120, "safety": 150}],
        prior=snapshot,
        pinned={TaskId(UUID(int=1))},
    )

    output = plan(value)

    assert output.base_plan is not None
    allocation = next(
        item for item in output.base_plan.allocations if item.task_id == TaskId(UUID(int=1))
    )
    assert allocation.start_at == snapshot.allocations[0].start_at
    assert allocation.end_at == snapshot.allocations[0].end_at
    assert "PROPOSAL_REQUIRED:USER_PINNED_MOVE_FORBIDDEN" in output.validation_warnings


def test_public_plan_preserves_freeze_window_allocation_until_proposal_is_approved() -> None:
    from personal_pm_planner import plan

    snapshot = PriorPlanSnapshot(
        id=UUID(int=901),
        input_hash="prior",
        allocations=(
            PriorAllocation(
                task_id=TaskId(UUID(int=1)),
                start_at=datetime(2026, 9, 1, 1, 30, tzinfo=UTC),
                end_at=datetime(2026, 9, 1, 2, 30, tzinfo=UTC),
            ),
        ),
    )
    value = build_value(
        task_specs=[{"base": 60, "safety": 90}],
        prior=snapshot,
    )

    output = plan(value)

    assert output.base_plan is not None
    allocation = next(
        item for item in output.base_plan.allocations if item.task_id == TaskId(UUID(int=1))
    )
    assert allocation.start_at == snapshot.allocations[0].start_at
    assert allocation.end_at == snapshot.allocations[0].end_at
    assert "PROPOSAL_REQUIRED:FREEZE_WINDOW_MOVE_FORBIDDEN" in output.validation_warnings


def test_public_plan_keeps_pinned_allocation_when_no_fresh_slot_exists() -> None:
    from personal_pm_planner import plan

    snapshot = PriorPlanSnapshot(
        id=UUID(int=902),
        input_hash="prior",
        allocations=(
            PriorAllocation(
                task_id=TaskId(UUID(int=1)),
                start_at=datetime(2026, 9, 1, 3, 30, tzinfo=UTC),
                end_at=datetime(2026, 9, 1, 4, 30, tzinfo=UTC),
            ),
        ),
    )
    value = replace(
        build_value(
            task_specs=[{"base": 60, "safety": 90}],
            prior=snapshot,
            pinned={TaskId(UUID(int=1))},
        ),
        availability_windows=(),
    )

    output = plan(value)

    assert output.base_plan is not None
    assert [
        (item.start_at, item.end_at)
        for item in output.base_plan.allocations
        if item.task_id == TaskId(UUID(int=1))
    ] == [(snapshot.allocations[0].start_at, snapshot.allocations[0].end_at)]


def test_choose_candidate_uses_lexicographic_field_order() -> None:
    from personal_pm_planner.replanning.cost import LEXICOGRAPHIC_FIELDS, ReplanMetrics
    from personal_pm_planner.replanning.optimize import choose_candidate

    safer_but_costly = ReplanMetrics(
        hard_constraint_violations=0,
        authorization_violations=0,
        critical_milestones=0,
        base_unallocated_minutes=0,
        high_milestones=1,
        safety_unallocated_minutes=30,
        change_cost=500,
        context_switches=5,
        energy_mismatch=5,
    )
    cheaper_but_risky = ReplanMetrics(
        hard_constraint_violations=0,
        authorization_violations=0,
        critical_milestones=1,
        base_unallocated_minutes=0,
        high_milestones=0,
        safety_unallocated_minutes=0,
        change_cost=10,
        context_switches=0,
        energy_mismatch=0,
    )
    chosen = choose_candidate((safer_but_costly, cheaper_but_risky))
    # Safety precedes change cost regardless of magnitude.
    assert chosen is safer_but_costly
    assert len(LEXICOGRAPHIC_FIELDS) == 9


def test_today_plan_structure_and_excluded_work() -> None:
    from personal_pm_planner.risk.classify import build_risk_context, calculate_risks
    from personal_pm_planner.scheduling.passes import run_planning_passes
    from personal_pm_planner.today import build_today_plan

    value = build_value(
        task_specs=[
            {"base": 120, "safety": 150},
            {"base": 240, "safety": 300},
        ]
    )
    passes = run_planning_passes(value)
    risks = calculate_risks(passes, build_risk_context(value))
    today = build_today_plan(value, passes, risks)

    assert len(today.must_do) >= 1
    assert today.core_result_task_id is not None
    # Capacity-excluded work appears explicitly, never silently dropped.
    assert all(
        task_id in set(today.must_do) | set(today.next_queue) | set(today.excluded)
        for task_id in (TaskId(UUID(int=1)), TaskId(UUID(int=2)))
    )


def test_today_plan_uses_user_local_date_at_utc_boundary() -> None:
    from personal_pm_planner.domain.availability import AvailabilityWindow
    from personal_pm_planner.risk.classify import build_risk_context, calculate_risks
    from personal_pm_planner.scheduling.passes import run_planning_passes
    from personal_pm_planner.today import build_today_plan

    local_day_now = datetime(2026, 9, 1, 15, 30, tzinfo=UTC)
    value = replace(
        build_value(task_specs=[{"base": 60, "safety": 60}]),
        now_utc=local_day_now,
        availability_windows=(
            AvailabilityWindow(
                start_at=local_day_now,
                end_at=local_day_now + timedelta(hours=3),
                tags=frozenset({"focus"}),
            ),
        ),
    )
    passes = run_planning_passes(value)
    risks = calculate_risks(passes, build_risk_context(value))
    allocation = next(
        item for item in passes.base.allocations if item.task_id == TaskId(UUID(int=1))
    )

    assert allocation.start_at.date() != date(2026, 9, 2)
    assert allocation.start_at.astimezone(ZoneInfo("Asia/Seoul")).date() == date(2026, 9, 2)
    assert TaskId(UUID(int=1)) in build_today_plan(value, passes, risks).must_do
