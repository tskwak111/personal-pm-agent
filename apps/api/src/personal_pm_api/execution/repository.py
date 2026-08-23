"""Transactional outbox and execution repositories."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.execution.models import ExternalExecutionModel, OutboxEventModel


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workspace_id: UUID,
        operation_id: UUID | None,
        idempotency_key: str,
        command_type: str,
        payload: dict[str, object],
    ) -> OutboxEventModel:
        record = OutboxEventModel(
            id=uuid4(),
            workspace_id=workspace_id,
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            command_type=command_type,
            payload=payload,
            status="pending",
            attempts=0,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def pending_batch(self, limit: int = 50) -> Sequence[OutboxEventModel]:
        statement = (
            select(OutboxEventModel)
            .where(OutboxEventModel.status == "pending")
            .order_by(OutboxEventModel.created_at)
            .limit(limit)
        )
        return list((await self._session.execute(statement)).scalars())


class ExternalExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def apply_pending(
        self,
        *,
        outbox_event_id: UUID,
        idempotency_key: str,
        provider: str = "google_calendar",
    ) -> ExternalExecutionModel:
        model = ExternalExecutionModel(
            id=uuid4(),
            outbox_event_id=outbox_event_id,
            idempotency_key=idempotency_key,
            provider=provider,
            external_id=None,
            result_status="Pending",
            verified=False,
            executed_at=self._now(),
        )
        self._session.add(model)
        await self._session.flush()
        return model

    @staticmethod
    def _now() -> datetime:
        from datetime import UTC, datetime

        return datetime.now(UTC)
