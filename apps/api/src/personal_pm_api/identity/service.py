"""Identity service: user provisioning (test provider) and actor resolution."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.identity.session import (
    CurrentActor,
    hash_session_token,
    mint_session,
    resolve_actor_from_rows,
)
from personal_pm_api.workspaces.models import UserModel


@dataclass(frozen=True, slots=True)
class IssuedSession:
    raw_token: str
    user_id: UUID
    session_id: UUID


class IdentityService:
    """Server-session identity. Google OIDC attaches in Phase 5 behind the same port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_user(self, *, email: str, display_name: str) -> UserModel:

        statement = select(UserModel).where(UserModel.email == email)
        existing = (await self._session.execute(statement)).scalar_one_or_none()
        if existing is not None:
            return existing
        user = UserModel(email=email, display_name=display_name)
        self._session.add(user)
        await self._session.flush()
        return user

    async def start_session_for_user(self, user_id: UUID) -> IssuedSession:
        model, raw_token = mint_session(user_id)
        self._session.add(model)
        await self._session.flush()
        return IssuedSession(raw_token=raw_token, user_id=user_id, session_id=model.id)

    async def ensure_workspace(self, *, user_id: UUID, name: str) -> None:
        from personal_pm_api.workspaces.models import WorkspaceModel

        existing = (
            await self._session.execute(
                select(WorkspaceModel.id).where(WorkspaceModel.owner_user_id == user_id).limit(1)
            )
        ).scalar_one_or_none()
        if existing is None:
            self._session.add(WorkspaceModel(owner_user_id=user_id, name=name))
            await self._session.flush()

    async def test_provider_session(self, *, email: str) -> IssuedSession:
        """Deterministic provider mounted only in local/test applications."""
        user = await self.ensure_user(email=email, display_name=email.split("@")[0])
        await self.ensure_workspace(user_id=user.id, name="내 워크스페이스")
        return await self.start_session_for_user(user.id)

    async def resolve_actor(self, raw_token: str) -> CurrentActor | None:
        from personal_pm_api.identity.repository import SessionRepository

        sessions = SessionRepository(self._session)
        row = await sessions.get_by_token_hash(hash_session_token(raw_token))
        row_actor = resolve_actor_from_rows(row, now_utc=datetime.now(UTC))
        if row_actor is None:
            return None
        workspace_id = await sessions.primary_workspace_id(row_actor.user_id)
        if workspace_id is None:
            return None
        return replace(row_actor, workspace_id=workspace_id)
