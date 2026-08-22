from datetime import UTC, datetime
from uuid import UUID

import pytest
from personal_pm_planner.domain.availability import (
    AvailabilityWindow,
    CalendarEventSnapshot,
    ExternalDependencySnapshot,
)
from personal_pm_planner.domain.enums import CalendarEventKind
from personal_pm_planner.domain.identifiers import (
    CalendarEventId,
    ExternalDependencyId,
    TaskId,
    WorkspaceId,
)

WORKSPACE = WorkspaceId(UUID("00000000-0000-0000-0000-000000000001"))


@pytest.fixture
def aware_datetime():
    def factory(hour: int, minute: int = 0) -> datetime:
        return datetime(2026, 8, 23, hour, minute, tzinfo=UTC)

    return factory


def test_availability_requires_positive_window(aware_datetime) -> None:
    start = aware_datetime(12, 0)
    with pytest.raises(ValueError, match="end must be after start"):
        AvailabilityWindow(start_at=start, end_at=start, tags=frozenset())


def test_availability_rejects_naive_bounds(aware_datetime) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        AvailabilityWindow(
            start_at=datetime(2026, 8, 23, 9, 0),
            end_at=aware_datetime(10, 0),
            tags=frozenset({"focus"}),
        )


def test_calendar_event_kinds_are_canonical() -> None:
    assert {kind.value for kind in CalendarEventKind} == {
        "fixed_busy",
        "movable_commitment",
        "tentative",
        "all_day_info",
    }


def test_calendar_event_window_must_be_positive(aware_datetime) -> None:
    with pytest.raises(ValueError, match="end must be after start"):
        CalendarEventSnapshot(
            id=CalendarEventId(UUID(int=11)),
            workspace_id=WORKSPACE,
            title="데이터베이스 수업",
            start_at=aware_datetime(9, 0),
            end_at=aware_datetime(9, 0),
            event_kind=CalendarEventKind.FIXED_BUSY,
            deadline_date=None,
            version=1,
        )


def test_external_dependency_requires_affected_tasks() -> None:
    with pytest.raises(ValueError, match="affected task"):
        ExternalDependencySnapshot(
            id=ExternalDependencyId(UUID(int=12)),
            workspace_id=WORKSPACE,
            deliverable="팀원의 데이터셋 정리",
            owner_label="민수",
            expected_delivery_at=datetime(2026, 8, 26, 12, 0, tzinfo=UTC),
            uncertainty_buffer_minutes=120,
            fallback_available=False,
            fallback_task_ids=(),
            affected_task_ids=(),
            version=1,
        )


def test_external_dependency_rejects_negative_buffer() -> None:
    with pytest.raises(ValueError, match="uncertainty_buffer_minutes"):
        ExternalDependencySnapshot(
            id=ExternalDependencyId(UUID(int=12)),
            workspace_id=WORKSPACE,
            deliverable="팀원의 데이터셋 정리",
            owner_label=None,
            expected_delivery_at=None,
            uncertainty_buffer_minutes=-1,
            fallback_available=False,
            fallback_task_ids=(),
            affected_task_ids=(TaskId(UUID(int=13)),),
            version=1,
        )
