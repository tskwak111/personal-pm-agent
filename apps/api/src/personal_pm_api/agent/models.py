"""Agent operation ORM models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from personal_pm_api.shared.orm import Base, created_at, pk_uuid


class AgentOperationModel(Base):
    __tablename__ = "agent_operations"

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_text: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    created_at: Mapped[datetime] = created_at()


class OperationStepEventModel(Base):
    __tablename__ = "operation_step_events"
    __table_args__ = (CheckConstraint("sequence >= 0", name="nonnegative_sequence"),)

    id: Mapped[UUID] = pk_uuid()
    operation_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("agent_operations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = created_at()
