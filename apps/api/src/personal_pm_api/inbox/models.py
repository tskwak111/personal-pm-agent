"""Source artifact ORM models (immutable upload records)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from personal_pm_api.shared.orm import Base, created_at, pk_uuid


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
