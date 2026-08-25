"""Analytics ORM models: work sessions and estimation profiles."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from personal_pm_api.shared.orm import Base, created_at, pk_uuid


class WorkSessionModel(Base):
    __tablename__ = "work_sessions"

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    actual_focus_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_reason: Mapped[str | None] = mapped_column(Text())
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()


class EstimationProfileModel(Base):
    __tablename__ = "estimation_profiles"

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
