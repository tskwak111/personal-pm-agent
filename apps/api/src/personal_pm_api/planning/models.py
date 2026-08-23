"""Planning Core relational models (normalized, versioned, workspace-scoped)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from personal_pm_api.shared.orm import Base, created_at, pk_uuid, updated_at


class AreaModel(Base):
    __tablename__ = "areas"

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class WorkstreamModel(Base):
    __tablename__ = "workstreams"

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    area_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("areas.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    importance: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class MilestoneModel(Base):
    __tablename__ = "milestones"
    __table_args__ = (
        CheckConstraint(
            "(deadline_time_known = false) OR (deadline_at IS NOT NULL)",
            name="known_time_requires_instant",
        ),
        CheckConstraint(
            "(deadline_time_known = true) OR (deadline_at IS NULL)",
            name="unknown_time_forbids_instant",
        ),
        CheckConstraint("required_buffer_minutes >= 0", name="buffer_nonnegative"),
    )

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workstream_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workstreams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    deadline_date: Mapped[date | None] = mapped_column(Date())
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_date_known: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deadline_time_known: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deadline_type: Mapped[str] = mapped_column(String(30), nullable=False)
    required_buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class TaskModel(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("base_duration_minutes > 0", name="base_positive"),
        CheckConstraint(
            "safety_duration_minutes >= base_duration_minutes",
            name="safety_gte_base",
        ),
        CheckConstraint(
            "(status NOT IN ('done','cancelled')) OR "
            "(remaining_base_minutes = 0 AND remaining_safety_minutes = 0)",
            name="terminal_has_no_remaining",
        ),
        CheckConstraint(
            "(deadline_time_known = false) OR (deadline_at IS NOT NULL)",
            name="known_time_requires_instant",
        ),
        CheckConstraint("min_chunk_minutes > 0", name="chunk_positive"),
    )

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workstream_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workstreams.id", ondelete="CASCADE"), nullable=False
    )
    milestone_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("milestones.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    deadline_date: Mapped[date | None] = mapped_column(Date())
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_time_known: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    start_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    base_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_base_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_safety_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    uncertainty: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    splittable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_chunk_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    waiting_reason: Mapped[str | None] = mapped_column(Text())
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class TaskDependencyModel(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (CheckConstraint("predecessor_id <> successor_id", name="no_self_dependency"),)

    predecessor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    successor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    dependency_type: Mapped[str] = mapped_column(String(25), primary_key=True)


class CalendarEventModel(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="positive_window"),
        # One ACTIVE provider event per provider identity; tombstones may repeat.
        Index(
            "uq_calendar_events_active_provider_identity",
            "external_calendar_id",
            "external_event_id",
            unique=True,
            postgresql_where=text("sync_status <> 'tombstoned'"),
        ),
    )

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_calendar_id: Mapped[str] = mapped_column(String(200), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    external_version: Mapped[int | None] = mapped_column(Integer())
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_kind: Mapped[str] = mapped_column(String(25), nullable=False)
    deadline_date: Mapped[date | None] = mapped_column(Date())
    sync_status: Mapped[str] = mapped_column(String(25), nullable=False, default="pending_inbound")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class AvailabilityWindowModel(Base):
    __tablename__ = "availability_windows"
    __table_args__ = (CheckConstraint("end_at > start_at", name="positive_window"),)

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tags_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = created_at()


class PlanSnapshotModel(Base):
    __tablename__ = "plan_snapshots"

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    planner_version: Mapped[str] = mapped_column(String(40), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text(), nullable=False, default="manual")
    output_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = created_at()


Index(
    "uq_plan_snapshots_one_current_per_workspace",
    PlanSnapshotModel.workspace_id,
    unique=True,
    postgresql_where=PlanSnapshotModel.is_current.is_(True),
)
