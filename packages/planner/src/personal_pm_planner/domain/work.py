"""Immutable work-hierarchy snapshots: Areas, Workstreams and Milestones."""

from dataclasses import dataclass
from datetime import date, datetime

from personal_pm_planner.domain.enums import DeadlineType, ImportanceLevel, WorkstreamStatus
from personal_pm_planner.domain.identifiers import AreaId, MilestoneId, WorkspaceId, WorkstreamId
from personal_pm_planner.domain.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class AreaSnapshot:
    id: AreaId
    workspace_id: WorkspaceId
    name: str
    version: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("area name must not be empty")
        if self.version < 1:
            raise ValueError("version must be positive")


@dataclass(frozen=True, slots=True)
class WorkstreamSnapshot:
    id: WorkstreamId
    workspace_id: WorkspaceId
    area_id: AreaId
    name: str
    importance: ImportanceLevel
    status: WorkstreamStatus
    version: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("workstream name must not be empty")
        if self.version < 1:
            raise ValueError("version must be positive")


@dataclass(frozen=True, slots=True)
class MilestoneSnapshot:
    id: MilestoneId
    workspace_id: WorkspaceId
    workstream_id: WorkstreamId
    title: str
    deadline_date: date | None
    deadline_at: datetime | None
    deadline_date_known: bool
    deadline_time_known: bool
    deadline_type: DeadlineType
    required_buffer_minutes: int
    version: int

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("milestone title must not be empty")
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.required_buffer_minutes < 0:
            raise ValueError("required_buffer_minutes must not be negative")
        if self.deadline_at is not None:
            normalized = require_aware_utc(self.deadline_at)
            object.__setattr__(self, "deadline_at", normalized)
        if self.deadline_time_known and self.deadline_at is None:
            raise ValueError("known deadline time requires deadline_at")
        if not self.deadline_time_known and self.deadline_at is not None:
            raise ValueError("unknown deadline time cannot persist a factual deadline_at")
        if self.deadline_date is None and self.deadline_date_known:
            raise ValueError("deadline_date_known requires deadline_date")
