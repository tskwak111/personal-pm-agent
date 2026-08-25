"""External calendar event snapshots (provider-owned availability)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from personal_pm_api.shared.orm import Base, created_at, pk_uuid


class ExternalCalendarEventModel(Base):
    __tablename__ = "external_calendar_events"

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blocks_capacity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    availability_type: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed")
    managed_focus_block: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pending_internal_reconciliation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    outbound_restore_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sync_status: Mapped[str] = mapped_column(String(25), nullable=False, default="SYNCED")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_version: Mapped[int | None] = mapped_column(Integer())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
