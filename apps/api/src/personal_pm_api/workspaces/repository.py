"""Workspace-scoped repository for workstreams."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.planning.models import WorkstreamModel


class WorkstreamRepository:
    """All queries are workspace-scoped; cross-tenant reads are impossible here."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workspace_id: UUID,
        name: str,
        importance: str,
        status: str,
    ) -> WorkstreamModel:
        model = WorkstreamModel(
            id=uuid4(),
            workspace_id=workspace_id,
            area_id=None,
            name=name,
            importance=importance,
            status=status,
            version=1,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get(self, workspace_id: UUID, workstream_id: UUID) -> WorkstreamModel | None:
        statement = select(WorkstreamModel).where(
            WorkstreamModel.id == workstream_id,
            WorkstreamModel.workspace_id == workspace_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def count(self, workspace_id: UUID) -> int:
        statement = (
            select(func.count())
            .select_from(WorkstreamModel)
            .where(WorkstreamModel.workspace_id == workspace_id)
        )
        return int(await self._session.scalar(statement))
