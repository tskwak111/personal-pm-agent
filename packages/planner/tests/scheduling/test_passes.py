from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from personal_pm_planner.contracts.input import PlannerInput
from personal_pm_planner.domain.identifiers import MilestoneId

from tests.conftest import make_milestone, make_task

MILESTONE = MilestoneId(UUID(int=200))
NOW = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
DEADLINE = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def make_case(*, task_specs, buffer_minutes=0, availability_hours, start_utc=None):
    windows = ()
    if availability_hours:
        from personal_pm_planner.domain.availability import AvailabilityWindow

        window_start = start_utc or NOW
        windows = (
            AvailabilityWindow(
                start_at=window_start,
                end_at=window_start + timedelta(hours=availability_hours),
                tags=frozenset({"focus"}),
            ),
        )
    return PlannerInput(
        planner_version="planner-spec-1.0",
        now_utc=NOW,
        user_timezone="Asia/Seoul",
        horizon_end_utc=DEADLINE + timedelta(days=1),
        slot_minutes=15,
        availability_windows=windows,
        calendar_events=(),
        tasks=tuple(make_task(offset, **spec) for offset, spec in enumerate(task_specs, start=1)),
        milestones=(
            make_milestone(
                deadline_date=None,
                deadline_at=DEADLINE,
                deadline_date_known=False,
                deadline_time_known=True,
                required_buffer_minutes=buffer_minutes,
            ),
        ),
        task_dependencies=(),
        external_dependencies=(),
        pinned_task_ids=frozenset(),
        excluded_dates=(),
    )


@pytest.fixture
def tv09_case():
    """TV-09: Base 4h feasible, Safety 6h infeasible under 5h capacity."""
    # One Seoul-local day: 00:30-06:45 UTC == 09:30-15:45 KST.
    # 375 raw minutes * 0.80 = 300min planned capacity.
    value = make_case(
        task_specs=[
            {"base": 120, "safety": 180},
            {"base": 120, "safety": 180},
        ],
        buffer_minutes=0,
        availability_hours=6.25,
        start_utc=datetime(2026, 9, 1, 0, 30, tzinfo=UTC),
    )
    return {"input": value}


@pytest.fixture
def buffer_case():
    """One small task plus a 90-minute mandatory review/submission buffer."""
    value = make_case(
        task_specs=[{"base": 60, "safety": 75}],
        buffer_minutes=90,
        availability_hours=4,
    )
    return {"input": value}


def test_base_and_safety_passes_use_independent_ledgers(tv09_case) -> None:
    from personal_pm_planner.scheduling.passes import run_planning_passes

    result = run_planning_passes(tv09_case["input"])
    assert result.base.total_allocated_minutes == 240
    assert result.safety.total_allocated_minutes == 300
    assert result.base.slot_ledger is not result.safety.slot_ledger


def test_safety_pass_leaves_deficit_unallocated(tv09_case) -> None:
    from personal_pm_planner.scheduling.passes import run_planning_passes

    result = run_planning_passes(tv09_case["input"])
    assert len(result.safety.unallocated_task_ids) == 1


def test_synthetic_buffers_consume_real_slots(buffer_case) -> None:
    from personal_pm_planner.scheduling.passes import run_planning_passes

    result = run_planning_passes(buffer_case["input"])
    kinds = {item.kind for item in result.safety.allocations}
    assert {"REVIEW_BUFFER", "SUBMISSION_BUFFER"} <= kinds


def test_infeasible_required_path_is_promoted_to_p0_once() -> None:
    from personal_pm_planner.scheduling.passes import run_planning_passes

    # Two heavy P2-class tasks cannot both fit; promotion round runs exactly once.
    value = make_case(
        task_specs=[
            {"base": 200, "safety": 260},
            {"base": 200, "safety": 260},
        ],
        buffer_minutes=0,
        availability_hours=3.125,  # 150min capacity at 0.80
    )
    result = run_planning_passes(value)
    assert result.promoted_task_count >= 1
    assert result.base.total_allocated_minutes == result.provisional.total_allocated_minutes
