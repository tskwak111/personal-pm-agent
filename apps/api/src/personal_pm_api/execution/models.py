"""Transactional outbox and external execution records."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from personal_pm_api.shared.orm import Base, created_at, pk_uuid


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operation_id: Mapped[UUID | None] = mapped_column(Uuid)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    command_type: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(25), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = created_at()


class ExternalExecutionModel(Base):
    __tablename__ = "external_executions"
    __table_args__ = (
        CheckConstraint(
            "verified = false OR external_id IS NOT NULL", name="verified_has_external_id"
        ),
        Index("ix_external_executions_outbox_unique", "outbox_event_id", unique=True),
    )

    id: Mapped[UUID] = pk_uuid()
    outbox_event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("outbox_events.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(200))
    result_status: Mapped[str] = mapped_column(String(30), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("ix_outbox_events_pending_delivery", OutboxEventModel.status, OutboxEventModel.created_at)
