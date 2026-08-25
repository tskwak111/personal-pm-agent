"""Inbox ORM models: immutable source artifacts, items and candidates."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from personal_pm_api.shared.errors import DomainRuleError
from personal_pm_api.shared.orm import Base, created_at, pk_uuid

INBOX_TRANSITIONS = {
    "NEW": {"PROCESSING", "IGNORED"},
    "PROCESSING": {"NEEDS_CONFIRMATION", "STRUCTURED", "FAILED"},
    "NEEDS_CONFIRMATION": {"STRUCTURED", "IGNORED", "PROCESSING"},
    "FAILED": {"PROCESSING", "IGNORED"},
    "STRUCTURED": set(),
    "IGNORED": set(),
}


def transition_inbox(current: str, target: str) -> str:
    allowed = INBOX_TRANSITIONS.get(current)
    if allowed is None:
        raise DomainRuleError("UNKNOWN_INBOX_STATUS", f"unknown status {current}")
    if target not in allowed:
        raise DomainRuleError(
            "INVALID_INBOX_TRANSITION", f"{current} cannot transition to {target}"
        )
    return target


class SourceArtifactModel(Base):
    __tablename__ = "source_artifacts"

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="file")
    created_at: Mapped[datetime] = created_at()


class InboxItemModel(Base):
    __tablename__ = "inbox_items"
    __table_args__ = (CheckConstraint("kind IN ('file','text','image')", name="valid_kind"),)

    id: Mapped[UUID] = pk_uuid()
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_artifact_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("source_artifacts.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(25), nullable=False, default="NEW")
    failure_reason: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CandidateFactModel(Base):
    __tablename__ = "candidate_facts"

    id: Mapped[UUID] = pk_uuid()
    inbox_item_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("inbox_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    evidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    decision: Mapped[str] = mapped_column(String(30), nullable=False, default="HOLD")
    created_at: Mapped[datetime] = created_at()
