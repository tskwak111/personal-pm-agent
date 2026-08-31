"""Bounded, fail-closed database Outbox worker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from personal_pm_api.execution.models import ExternalExecutionModel
from personal_pm_api.execution.repository import OutboxRepository
from sqlalchemy import select


@dataclass(frozen=True, slots=True)
class OutboxCommand:
    id: UUID
    workspace_id: UUID
    idempotency_key: str
    command_type: str
    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class VerifiedExecution:
    external_id: str | None
    verified: bool


class OutboxExecutor(Protocol):
    async def execute(self, command: OutboxCommand) -> VerifiedExecution: ...


@dataclass(frozen=True, slots=True)
class WorkerRunResult:
    claimed: int
    succeeded: int
    failed: int


async def run_once(
    session_factory: Callable[[], Any],
    executor: OutboxExecutor | None,
    batch_size: int,
) -> WorkerRunResult:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    claimed = succeeded = failed = 0

    for _ in range(batch_size):
        async with session_factory() as session:
            pending = await OutboxRepository(session).pending_batch(limit=1)
            if not pending:
                break
            record = pending[0]
            claimed += 1
            record.attempts += 1
            execution = (
                await session.execute(
                    select(ExternalExecutionModel)
                    .where(ExternalExecutionModel.outbox_event_id == record.id)
                    .with_for_update()
                )
            ).scalar_one_or_none()

            if executor is None:
                _mark_failed(record, execution, "executor unavailable")
                failed += 1
            else:
                command = OutboxCommand(
                    id=record.id,
                    workspace_id=record.workspace_id,
                    idempotency_key=record.idempotency_key,
                    command_type=record.command_type,
                    payload=dict(record.payload),
                )
                try:
                    result = await executor.execute(command)
                except TimeoutError:
                    record.status = "pending"
                    record.last_error = "provider outcome unknown"
                    failed += 1
                except Exception as error:  # provider adapters are an explicit trust boundary
                    _mark_failed(record, execution, f"provider error:{type(error).__name__}")
                    failed += 1
                else:
                    if execution is not None and result.verified and result.external_id:
                        record.status = "succeeded"
                        record.last_error = None
                        execution.result_status = "Succeeded"
                        execution.external_id = result.external_id
                        execution.verified = True
                        succeeded += 1
                    else:
                        _mark_failed(record, execution, "provider result unverified")
                        failed += 1
            await session.commit()

    return WorkerRunResult(claimed=claimed, succeeded=succeeded, failed=failed)


def _mark_failed(record: Any, execution: Any, reason: str) -> None:
    record.status = "failed"
    record.last_error = reason
    if execution is not None:
        execution.result_status = "Failed"
        execution.external_id = None
        execution.verified = False


__all__ = [
    "OutboxCommand",
    "OutboxExecutor",
    "VerifiedExecution",
    "WorkerRunResult",
    "run_once",
]
