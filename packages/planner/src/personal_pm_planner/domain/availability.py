"""Availability, calendar event and external dependency snapshots.

Calendar events describe observed provider facts; external dependencies model
results other people owe the user and are never controllable tasks.
"""

from dataclasses import dataclass
from datetime import date, datetime

from personal_pm_planner.domain.enums import CalendarEventKind
from personal_pm_planner.domain.identifiers import (
    CalendarEventId,
    ExternalDependencyId,
    TaskId,
    WorkspaceId,
)
from personal_pm_planner.domain.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class AvailabilityWindow:
    start_at: datetime
    end_at: datetime
    tags: frozenset[str]

    def __post_init__(self) -> None:
        require_aware_utc(self.start_at)
        require_aware_utc(self.end_at)
        if self.end_at <= self.start_at:
            raise ValueError("end must be after start")

    @property
    def minutes(self) -> int:
        return int((self.end_at - self.start_at).total_seconds() // 60)


@dataclass(frozen=True, slots=True)
class CalendarEventSnapshot:
    id: CalendarEventId
    workspace_id: WorkspaceId
    title: str
    start_at: datetime
    end_at: datetime
    event_kind: CalendarEventKind
    deadline_date: date | None
    version: int

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("calendar event title must not be empty")
        require_aware_utc(self.start_at)
        require_aware_utc(self.end_at)
        if self.end_at <= self.start_at:
            raise ValueError("end must be after start")
        object.__setattr__(self, "event_kind", CalendarEventKind(self.event_kind))
        if self.version < 1:
            raise ValueError("version must be positive")


@dataclass(frozen=True, slots=True)
class ExternalDependencySnapshot:
    id: ExternalDependencyId
    workspace_id: WorkspaceId
    deliverable: str
    owner_label: str | None
    expected_delivery_at: datetime | None
    uncertainty_buffer_minutes: int
    fallback_available: bool
    fallback_task_ids: tuple[TaskId, ...]
    affected_task_ids: tuple[TaskId, ...]
    version: int

    def __post_init__(self) -> None:
        if not self.deliverable.strip():
            raise ValueError("external dependency deliverable must not be empty")
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.uncertainty_buffer_minutes < 0:
            raise ValueError("uncertainty_buffer_minutes must not be negative")
        if not self.affected_task_ids:
            raise ValueError("external dependency requires at least one affected task")
        normalized_delivery = (
            None
            if self.expected_delivery_at is None
            else require_aware_utc(self.expected_delivery_at)
        )
        object.__setattr__(self, "expected_delivery_at", normalized_delivery)
