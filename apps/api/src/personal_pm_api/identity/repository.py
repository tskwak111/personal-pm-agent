"""Session and user lookups."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.identity.models import UserSessionModel
from personal_pm_api.workspaces.models import UserModel


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_token_hash(self, token_hash: str) -> UserSessionModel | None:
        statement = select(UserSessionModel).where(UserSessionModel.token_hash == token_hash)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def primary_workspace_id(self, owner_user_id: UUID) -> UUID | None:
        statement = select(UserModel.id).where(UserModel.id == owner_user_id)
        found = (await self._session.execute(statement)).scalar_one_or_none()
        if found is None:
            return None
        from personal_pm_api.workspaces.models import WorkspaceModel

        ws_statement = (
            select(WorkspaceModel.id).where(WorkspaceModel.owner_user_id == owner_user_id).limit(1)
        )
        return (await self._session.execute(ws_statement)).scalar_one_or_none()


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> UserModel | None:
        statement = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
