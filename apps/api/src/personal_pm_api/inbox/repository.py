"""Workspace-scoped source artifact repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.inbox.models import SourceArtifactModel


class SourceArtifactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, artifact: SourceArtifactModel) -> SourceArtifactModel:
        self._session.add(artifact)
        await self._session.flush()
        return artifact

    async def get(self, workspace_id: object, artifact_id: object) -> SourceArtifactModel | None:
        statement = select(SourceArtifactModel).where(
            SourceArtifactModel.workspace_id == workspace_id,
            SourceArtifactModel.id == artifact_id,
        )
        return (await self._session.execute(statement)).scalar_one_or_none()
