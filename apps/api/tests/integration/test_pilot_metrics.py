from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

import pytest_asyncio


@pytest_asyncio.fixture
async def pilot_metrics() -> Any:
    from personal_pm_api.analytics.pilot import PilotMetrics

    return PilotMetrics()


class _Participant:
    def __init__(self, pid: str) -> None:
        self.id = pid


async def test_active_user_definition_requires_behavior_not_login(
    pilot_metrics: Any,
) -> None:
    # Logged in 7 days but no task actions / plan views → NOT active.
    login_only = pilot_metrics.week_four_active(days_used=7, task_actions=0, plan_views=0)
    assert login_only is False


def test_active_definition_matches_contract(pilot_metrics: Any) -> None:
    active = pilot_metrics.week_four_active(days_used=3, task_actions=5, plan_views=2)
    assert active is True
    borderline = pilot_metrics.week_four_active(days_used=2, task_actions=9, plan_views=5)
    assert borderline is False


async def test_system_caused_deadline_delay_is_never_averaged_away(
    pilot_metrics: Any,
) -> None:
    report = await pilot_metrics.build_outcome_report(
        system_caused_deadline_delays=1,
        outcomes={
            m: True
            for m in (
                "OUT-001",
                "OUT-002",
                "OUT-003",
                "OUT-004",
                "OUT-005",
                "OUT-006",
                "OUT-007",
                "OUT-008",
            )
        },
        s0_incidents=0,
    )
    assert report.system_caused_deadline_delays == 1
    assert report.release_eligible is False


async def test_clean_pilot_with_all_outcomes_is_eligible(pilot_metrics: Any) -> None:
    report = await pilot_metrics.build_outcome_report(
        system_caused_deadline_delays=0,
        outcomes={
            "OUT-001": True,
            "OUT-002": True,
            "OUT-003": True,
            "OUT-004": False,
            "OUT-005": True,
            "OUT-006": True,
            "OUT-007": True,
            "OUT-008": True,
        },
        s0_incidents=0,
    )
    assert report.release_eligible is True
