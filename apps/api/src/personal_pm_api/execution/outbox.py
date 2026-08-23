"""Transactional outbox enqueue: state + command commit together."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from personal_pm_api.execution.repository import ExternalExecutionRepository

if TYPE_CHECKING:
    from uuid import UUID

    from personal_pm_api.execution.models import OutboxEventModel
    from personal_pm_api.shared.unit_of_work import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class ExternalCommand:
    workspace_id: UUID
    operation_id: UUID
    idempotency_key: str
    command_type: str
    payload: dict[str, object]


async def enqueue_external_command(
    uow: SqlAlchemyUnitOfWork,
    command: ExternalCommand,
) -> OutboxEventModel:
    """Create the outbox record and its Pending execution in one transaction."""
    assert uow.outbox is not None and uow.external_state is not None
    record = await uow.outbox.create(
        workspace_id=command.workspace_id,
        operation_id=command.operation_id,
        idempotency_key=command.idempotency_key,
        command_type=command.command_type,
        payload=command.payload,
    )
    executions = ExternalExecutionRepository(uow.typed_session)
    await executions.apply_pending(
        outbox_event_id=record.id,
        idempotency_key=command.idempotency_key,
    )
    return record


def utc_now() -> datetime:
    return datetime.now(UTC)


__all__ = ["ExternalCommand", "enqueue_external_command"]
