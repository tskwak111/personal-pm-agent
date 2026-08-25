"""Typed agent operation lifecycle: append-only step events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from personal_pm_api.shared.errors import DomainRuleError

OPERATION_STEPS = (
    "OBSERVE",
    "INTERPRET",
    "RETRIEVE",
    "PLAN",
    "CRITIQUE",
    "AUTHORIZE",
    "ACT",
    "VERIFY",
    "EXPLAIN",
    "LEARN",
)


class InvalidOperationStepError(DomainRuleError):
    def __init__(self, step: str) -> None:
        super().__init__("INVALID_OPERATION_STEP", f"unknown operation step: {step}")


@dataclass(frozen=True, slots=True)
class OperationView:
    id: str
    status: str


@dataclass(frozen=True, slots=True)
class StepEventView:
    step: str
    status: str
    sequence: int


class AgentOperationService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def start(self, actor: Any, user_text: str) -> OperationView:
        from personal_pm_api.agent.models import AgentOperationModel

        async with self._factory() as session:
            model = AgentOperationModel(
                id=uuid4(),
                workspace_id=UUID(str(actor.workspace_id)),
                user_text=user_text,
                status="RUNNING",
            )
            session.add(model)
            await session.commit()
            return OperationView(id=str(model.id), status=model.status)

    async def get(self, actor: Any, operation_id: str) -> OperationView | None:

        async with self._factory() as session:
            model = await self._owned(session, actor, operation_id)
            if model is None:
                return None
            return OperationView(id=str(model.id), status=model.status)

    async def append_step(
        self,
        operation_id: str,
        step: str,
        status: str,
        payload: dict[str, object] | None = None,
    ) -> StepEventView:
        """Append without an actor check (worker-side usage)."""
        async with self._factory() as session:
            operation = await session.get(_operation_model(), UUID(str(operation_id)))
            if operation is None:
                from personal_pm_api.shared.errors import NotFoundError

                raise NotFoundError()
            return await self._append(session, operation, step, status, payload)

    async def append_step_for_actor(
        self,
        actor: Any,
        operation_id: str,
        step: str,
        status: str,
        payload: dict[str, object] | None = None,
    ) -> StepEventView:
        async with self._factory() as session:
            operation = await self._owned(session, actor, operation_id)
            if operation is None:
                from personal_pm_api.shared.errors import NotFoundError

                raise NotFoundError()
            return await self._append(session, operation, step, status, payload)

    async def events(self, actor: Any, operation_id: str) -> list[StepEventView]:
        from personal_pm_api.agent.models import OperationStepEventModel

        async with self._factory() as session:
            operation = await self._owned(session, actor, operation_id)
            if operation is None:
                from personal_pm_api.shared.errors import NotFoundError

                raise NotFoundError()
            rows = (
                (
                    await session.execute(
                        select(OperationStepEventModel)
                        .where(OperationStepEventModel.operation_id == operation.id)
                        .order_by(OperationStepEventModel.sequence)
                    )
                )
                .scalars()
                .all()
            )
            return [
                StepEventView(step=row.step, status=row.status, sequence=row.sequence)
                for row in rows
            ]

    async def _append(
        self,
        session: AsyncSession,
        operation: Any,
        step: str,
        status: str,
        payload: dict[str, object] | None,
    ) -> StepEventView:
        if step not in OPERATION_STEPS:
            raise InvalidOperationStepError(step)
        from personal_pm_api.agent.models import OperationStepEventModel

        sequence = len(await self._all_events(session, operation.id))
        event = OperationStepEventModel(
            id=uuid4(),
            operation_id=operation.id,
            step=step,
            status=status,
            payload=payload or {},
            sequence=sequence,
        )
        session.add(event)
        await session.commit()
        return StepEventView(step=event.step, status=event.status, sequence=sequence)

    @staticmethod
    async def _all_events(session: AsyncSession, operation_id: UUID) -> list[Any]:
        from personal_pm_api.agent.models import OperationStepEventModel

        return list(
            (
                await session.execute(
                    select(OperationStepEventModel).where(
                        OperationStepEventModel.operation_id == operation_id
                    )
                )
            ).scalars()
        )

    @staticmethod
    async def _owned(session: AsyncSession, actor: Any, operation_id: str) -> Any | None:
        from personal_pm_api.agent.models import AgentOperationModel

        statement = select(AgentOperationModel).where(
            AgentOperationModel.id == UUID(str(operation_id)),
            AgentOperationModel.workspace_id == UUID(str(actor.workspace_id)),
        )
        return (await session.execute(statement)).scalar_one_or_none()


def _operation_model() -> type[Any]:
    from personal_pm_api.agent.models import AgentOperationModel

    return AgentOperationModel  # type: ignore[return-value]


__all__ = ["AgentOperationService", "InvalidOperationStepError", "OPERATION_STEPS"]
