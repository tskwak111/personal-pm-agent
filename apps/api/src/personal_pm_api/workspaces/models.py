"""Workspace and user ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Ensure SA registry includes identity tables before mapper configure.
from personal_pm_api.identity import models as _identity_models  # noqa: F401
from personal_pm_api.shared.orm import Base, created_at, pk_uuid

if TYPE_CHECKING:
    from personal_pm_api.identity.models import UserSessionModel


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = pk_uuid()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = created_at()

    workspaces: Mapped[list[WorkspaceModel]] = relationship(
        back_populates="owner", passive_deletes=True
    )
    sessions: Mapped[list[UserSessionModel]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class WorkspaceModel(Base):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = pk_uuid()
    owner: Mapped[UserModel] = relationship(back_populates="workspaces")
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Asia/Seoul", server_default="Asia/Seoul"
    )
    created_at: Mapped[datetime] = created_at()
