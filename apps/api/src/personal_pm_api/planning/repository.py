"""Planning Core repositories (milestones, tasks, plan snapshots)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.planning.models import MilestoneModel, PlanSnapshotModel, TaskModel


class PlanningRepository:
    """Workspace-scoped access to planning aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_tasks(self, workspace_id: UUID) -> int:
        statement = (
            select(func.count())
            .select_from(TaskModel)
            .where(TaskModel.workspace_id == workspace_id)
        )
        return int(await self._session.scalar(statement))

    async def get_milestone(self, workspace_id: UUID, milestone_id: UUID) -> MilestoneModel | None:
        statement = select(MilestoneModel).where(
            MilestoneModel.id == milestone_id,
            MilestoneModel.workspace_id == workspace_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def latest_valid_plan(self, workspace_id: UUID) -> PlanSnapshotModel | None:
        statement = (
            select(PlanSnapshotModel)
            .where(
                PlanSnapshotModel.workspace_id == workspace_id,
                PlanSnapshotModel.is_current.is_(True),
            )
            .order_by(PlanSnapshotModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
