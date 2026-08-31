"""Encrypted persisted Calendar provider connections."""

from __future__ import annotations

import base64
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_pm_api.calendar.oauth import TokenResponse
from personal_pm_api.calendar.token_vault import TokenVault
from personal_pm_api.settings import ApiSettings
from personal_pm_api.shared.orm import Base, created_at, updated_at


class CalendarConnectionModel(Base):
    __tablename__ = "calendar_connections"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('READ_ONLY','READ_WRITE')",
            name="valid_mode",
        ),
        CheckConstraint(
            "status IN ('CONNECTED','NEEDS_REAUTHORIZATION','REVOKED')",
            name="valid_status",
        ),
        UniqueConstraint(
            "workspace_id",
            "provider",
            name="uq_calendar_connections_workspace_provider",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="google")
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    scopes_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    access_token_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    access_token_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    token_key_version: Mapped[int] = mapped_column(Integer, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


def token_vault(settings: ApiSettings) -> TokenVault:
    secret = settings.token_encryption_key
    if secret is None:
        raise ValueError("token encryption key is not configured")
    encoded = secret.get_secret_value().encode("ascii")
    try:
        key = base64.b64decode(encoded, altchars=b"-_", validate=True)
    except (ValueError, UnicodeError) as error:
        raise ValueError("token encryption key is invalid") from error
    return TokenVault(key)


async def persist_verified_connection(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    mode: str,
    tokens: TokenResponse,
    settings: ApiSettings,
) -> CalendarConnectionModel:
    from sqlalchemy import select

    vault = token_vault(settings)
    access = vault.encrypt(tokens.access_token, key_version=1)
    refresh = vault.encrypt(tokens.refresh_token, key_version=1)
    statement = (
        select(CalendarConnectionModel)
        .where(
            CalendarConnectionModel.workspace_id == workspace_id,
            CalendarConnectionModel.provider == "google",
        )
        .with_for_update()
    )
    model = (await session.execute(statement)).scalar_one_or_none()
    if model is None:
        model = CalendarConnectionModel(
            id=uuid4(),
            workspace_id=workspace_id,
            provider="google",
            mode=mode,
            status="CONNECTED",
            scopes_json=list(tokens.scopes),
            access_token_ciphertext=access.ciphertext,
            access_token_nonce=access.nonce,
            refresh_token_ciphertext=refresh.ciphertext,
            refresh_token_nonce=refresh.nonce,
            token_key_version=access.key_version,
            token_expires_at=tokens.expires_at,
        )
        session.add(model)
    else:
        model.mode = mode
        model.status = "CONNECTED"
        model.scopes_json = list(tokens.scopes)
        model.access_token_ciphertext = access.ciphertext
        model.access_token_nonce = access.nonce
        model.refresh_token_ciphertext = refresh.ciphertext
        model.refresh_token_nonce = refresh.nonce
        model.token_key_version = access.key_version
        model.token_expires_at = tokens.expires_at
    await session.flush()
    return model


__all__ = ["CalendarConnectionModel", "persist_verified_connection", "token_vault"]
