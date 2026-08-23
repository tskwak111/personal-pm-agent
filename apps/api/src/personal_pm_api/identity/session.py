"""Opaque bearer sessions with hashed-at-rest tokens."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.identity.models import UserSessionModel

SESSION_TTL_HOURS = 8


@dataclass(frozen=True, slots=True)
class CurrentActor:
    user_id: UUID
    workspace_id: UUID  # primary workspace, resolved at session resolution
    session_id: UUID


def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def mint_session(user_id: UUID) -> tuple[UserSessionModel, str]:
    """Return (persisted model, raw token shown once to the client)."""
    raw_token = secrets.token_urlsafe(32)
    model = UserSessionModel(
        id=uuid4(),
        user_id=user_id,
        token_hash=hash_session_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(hours=SESSION_TTL_HOURS),
    )
    return model, raw_token


def resolve_actor_from_rows(
    session_row: UserSessionModel | None,
    *,
    now_utc: datetime,
) -> CurrentActor | None:
    if session_row is None or session_row.expires_at <= now_utc:
        return None
    return CurrentActor(
        user_id=session_row.user_id,
        workspace_id=UUID(int=0),  # placeholder; service resolves real id
        session_id=session_row.id,
    )


async def find_session_by_token(session: AsyncSession, raw_token: str) -> UserSessionModel | None:
    statement = select(UserSessionModel).where(
        UserSessionModel.token_hash == hash_session_token(raw_token)
    )
    return (await session.execute(statement)).scalar_one_or_none()
