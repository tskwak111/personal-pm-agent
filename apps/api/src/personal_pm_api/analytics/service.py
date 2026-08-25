"""Work Session records and estimation profile analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

MAX_BACKOFF_FACTOR = 2.50
MIN_BACKOFF_FACTOR = 0.75


@dataclass(frozen=True, slots=True)
class SessionOutcome:
    status: str
    actual_focus_minutes: int = 0
    task_remaining_base_minutes: int = 0


@dataclass(frozen=True, slots=True)
class ProfileView:
    factor: float
    sample_count: int


def blended_factor(observed_ratio: float, sample_count: int) -> float:
    """Sample-count weighted blend; small samples never move the factor."""
    weight = (
        0.0
        if sample_count <= 2
        else 0.30
        if sample_count <= 5
        else 0.60
        if sample_count <= 19
        else 0.80
    )
    return min(
        MAX_BACKOFF_FACTOR,
        max(MIN_BACKOFF_FACTOR, round(1.0 + (observed_ratio - 1.0) * weight, 6)),
    )


class WorkSessionService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def start(self, actor: Any, *, task_id: str) -> Any:
        from personal_pm_api.analytics.models import WorkSessionModel
        from personal_pm_api.shared.errors import NotFoundError

        async with self._factory() as session:
            task = await self._owned_task(session, actor, task_id)
            if task is None:
                raise NotFoundError()
            record = WorkSessionModel(
                id=uuid4(),
                workspace_id=UUID(str(actor.workspace_id)),
                task_id=task.id,
                status="RUNNING",
                started_at=datetime.now(UTC),
            )
            session.add(record)
            await session.commit()
            return SessionView(record)

    async def partial_complete(
        self, actor: Any, *, session_id: str, remaining_base_minutes: int
    ) -> SessionOutcome:
        from personal_pm_api.planning.models import TaskModel

        async with self._factory() as session:
            record = await self._owned_record(session, actor, session_id)
            task = await session.get(TaskModel, record.task_id)
            assert task is not None
            actual = max(0, task.remaining_base_minutes - remaining_base_minutes)
            task.remaining_base_minutes = remaining_base_minutes
            task.version += 1
            record.status = "PARTIAL"
            record.actual_focus_minutes = actual
            await session.commit()
            return SessionOutcome(
                status="PARTIAL",
                actual_focus_minutes=actual,
                task_remaining_base_minutes=remaining_base_minutes,
            )

    async def complete(self, actor: Any, *, session_id: str) -> SessionOutcome:
        from personal_pm_api.planning.models import TaskModel

        async with self._factory() as session:
            record = await self._owned_record(session, actor, session_id)
            task = await session.get(TaskModel, record.task_id)
            assert task is not None
            actual = task.remaining_base_minutes
            task.remaining_base_minutes = 0
            task.remaining_safety_minutes = 0
            task.status = "done"
            task.version += 1
            record.status = "COMPLETED"
            record.actual_focus_minutes = actual
            await session.commit()
            return SessionOutcome(
                status="COMPLETED",
                actual_focus_minutes=actual,
                task_remaining_base_minutes=0,
            )

    async def block(self, actor: Any, *, session_id: str, reason: str) -> SessionOutcome:

        async with self._factory() as session:
            record = await self._owned_record(session, actor, session_id)
            record.status = "BLOCKED"
            record.blocked_reason = reason
            await session.commit()
            return SessionOutcome(status="BLOCKED")

    @staticmethod
    async def _owned_task(session: AsyncSession, actor: Any, task_id: str) -> Any | None:
        from personal_pm_api.planning.models import TaskModel

        statement = select(TaskModel).where(
            TaskModel.id == UUID(task_id),
            TaskModel.workspace_id == UUID(str(actor.workspace_id)),
        )
        return (await session.execute(statement)).scalar_one_or_none()

    async def _owned_record(self, session: AsyncSession, actor: Any, session_id: str) -> Any:
        from personal_pm_api.analytics.models import WorkSessionModel
        from personal_pm_api.shared.errors import NotFoundError

        statement = select(WorkSessionModel).where(
            WorkSessionModel.id == UUID(session_id),
            WorkSessionModel.workspace_id == UUID(str(actor.workspace_id)),
        )
        record = (await session.execute(statement)).scalar_one_or_none()
        if record is None:
            raise NotFoundError()
        return record


class SessionView:
    def __init__(self, model: Any) -> None:
        self.id = str(model.id)
        self.status = model.status


class EstimationProfileService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def recalculate(
        self, workspace_id: str, kind: str, observed_ratio: float, sample_count: int
    ) -> ProfileView:
        """Deterministic blended factor; persisted for briefing evidence."""
        from personal_pm_api.analytics.models import EstimationProfileModel

        factor = blended_factor(observed_ratio, sample_count)
        async with self._factory() as session:
            statement = select(EstimationProfileModel).where(
                EstimationProfileModel.workspace_id == UUID(workspace_id),
                EstimationProfileModel.kind == kind,
            )
            existing = (await session.execute(statement)).scalar_one_or_none()
            if existing is None:
                session.add(
                    EstimationProfileModel(
                        id=uuid4(),
                        workspace_id=UUID(workspace_id),
                        kind=kind,
                        factor=factor,
                        sample_count=sample_count,
                    )
                )
            else:
                existing.factor = factor
                existing.sample_count = sample_count
                existing.updated_at = datetime.now(UTC)
            await session.commit()
        return ProfileView(factor=factor, sample_count=sample_count)


__all__ = ["EstimationProfileService", "SessionOutcome", "WorkSessionService", "blended_factor"]
