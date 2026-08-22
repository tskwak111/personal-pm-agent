"""Immutable Task snapshots with deadline and estimate invariants."""

from dataclasses import dataclass
from datetime import date, datetime

from personal_pm_planner.domain.enums import TaskStatus, Uncertainty
from personal_pm_planner.domain.identifiers import MilestoneId, TaskId, WorkspaceId, WorkstreamId
from personal_pm_planner.domain.time import require_aware_utc


def _validate_deadline_facts(
    *,
    deadline_at: datetime | None,
    deadline_time_known: bool,
) -> datetime | None:
    if deadline_time_known and deadline_at is None:
        raise ValueError("known deadline time requires deadline_at")
    if not deadline_time_known and deadline_at is not None:
        raise ValueError("unknown deadline time cannot persist a factual deadline_at")
    return None if deadline_at is None else require_aware_utc(deadline_at)


@dataclass(frozen=True, slots=True)
class TaskSnapshot:
    id: TaskId
    workspace_id: WorkspaceId
    workstream_id: WorkstreamId
    milestone_id: MilestoneId | None
    title: str
    status: TaskStatus
    deadline_date: date | None
    deadline_at: datetime | None
    deadline_time_known: bool
    start_after: datetime | None
    base_duration_minutes: int
    safety_duration_minutes: int
    remaining_base_minutes: int
    remaining_safety_minutes: int
    uncertainty: Uncertainty
    splittable: bool
    min_chunk_minutes: int
    pinned: bool
    waiting_reason: str | None
    version: int

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("task title must not be empty")
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.base_duration_minutes <= 0:
            raise ValueError("base_duration_minutes must be positive")
        if self.safety_duration_minutes < self.base_duration_minutes:
            raise ValueError(
                "safety_duration_minutes cannot be below base_duration_minutes"
            )
        if self.min_chunk_minutes <= 0:
            raise ValueError("min_chunk_minutes must be positive")
        object.__setattr__(self, "status", TaskStatus(self.status))
        object.__setattr__(self, "uncertainty", Uncertainty(self.uncertainty))
        if self.status in (TaskStatus.DONE, TaskStatus.CANCELLED) and (
            self.remaining_base_minutes != 0 or self.remaining_safety_minutes != 0
        ):
            raise ValueError("done or cancelled tasks have no remaining minutes")
        if self.remaining_base_minutes < 0 or self.remaining_safety_minutes < 0:
            raise ValueError("remaining minutes must not be negative")
        normalized_deadline = _validate_deadline_facts(
            deadline_at=self.deadline_at,
            deadline_time_known=self.deadline_time_known,
        )
        object.__setattr__(self, "deadline_at", normalized_deadline)
        if self.start_after is not None:
            object.__setattr__(
                self, "start_after", require_aware_utc(self.start_after)
            )
