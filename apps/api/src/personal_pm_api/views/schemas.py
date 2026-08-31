"""Typed, read-only browser projections."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class TaskSummary(BaseModel):
    id: str
    title: str
    status: str
    remaining_minutes: int
    version: int


class FixedEvent(BaseModel):
    id: str
    title: str
    start_at: datetime
    end_at: datetime
    kind: str
    sync_status: str


class TodayResponse(BaseModel):
    plan_status: str
    core_outcome: TaskSummary | None
    fixed_events: list[FixedEvent]
    must_do: list[TaskSummary]
    queue: list[TaskSummary]
    not_today: list[TaskSummary]


class InboxCandidate(BaseModel):
    id: str
    inbox_item_id: str
    kind: str
    status: str
    source_text: str | None
    interpretation: dict[str, Any]
    evidence_score: float
    decision: str


class InboxResponse(BaseModel):
    candidates: list[InboxCandidate]


class ProjectSummary(BaseModel):
    id: str
    title: str
    status: str
    execution_progress: int
    risk_level: str
    risk_reasons: list[str]
    task_count: int
    done_count: int


class MilestoneSummary(BaseModel):
    id: str
    title: str
    status: str
    deadline_date: date | None
    deadline_at: datetime | None
    deadline_time_known: bool
    version: int


class ExternalDependencySummary(BaseModel):
    id: str
    deliverable: str
    owner_label: str | None
    expected_delivery_at: datetime | None
    fallback_available: bool
    version: int


class ProjectsResponse(BaseModel):
    projects: list[ProjectSummary]


class ProjectDetailResponse(BaseModel):
    project: ProjectSummary
    milestones: list[MilestoneSummary]
    tasks: list[TaskSummary]
    external_dependencies: list[ExternalDependencySummary]


class CalendarConnectionSummary(BaseModel):
    provider: str
    mode: str
    status: str


class CalendarEventSummary(BaseModel):
    id: str
    title: str
    start_at: datetime
    end_at: datetime
    all_day: bool
    kind: str
    sync_status: str


class CalendarResponse(BaseModel):
    connections: list[CalendarConnectionSummary]
    events: list[CalendarEventSummary]
    flexible_tasks: list[TaskSummary]


class ProposalSummary(BaseModel):
    id: str
    kind: str
    approval_level: str
    status: str
    version: int
    targets: list[dict[str, Any]]


class ReviewResponse(BaseModel):
    period_start: date
    period_end: date
    planned_minutes: int
    actual_minutes: int
    missed_minutes: int
    pending_proposals: list[ProposalSummary]


__all__ = [
    "CalendarResponse",
    "InboxResponse",
    "ProjectDetailResponse",
    "ProjectsResponse",
    "ReviewResponse",
    "TodayResponse",
]
