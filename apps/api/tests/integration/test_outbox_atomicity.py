from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest


async def _seed_workspace_id(uow_factory) -> UUID:
    from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

    async with uow_factory() as uow:
        user = UserModel(email="outbox@example.com", display_name="OB")
        uow.typed_session.add(user)
        await uow.typed_session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ob")
        uow.typed_session.add(workspace)
        await uow.commit()
        return workspace.id


def make_command(workspace_id: UUID, key: str = "idem-ob-1") -> dict:
    return {
        "workspace_id": workspace_id,
        "operation_id": uuid4(),
        "idempotency_key": key,
        "command_type": "CREATE_FOCUS_BLOCK",
        "payload": {"start_at": "2026-09-02T09:00:00Z", "minutes": 90},
    }


async def _counts(uow_factory) -> tuple[int, int]:
    from personal_pm_api.execution.models import ExternalExecutionModel, OutboxEventModel
    from sqlalchemy import func, select

    async with uow_factory() as uow:
        s = uow.typed_session
        outbox = int(await s.scalar(select(func.count()).select_from(OutboxEventModel)))
        executions = int(await s.scalar(select(func.count()).select_from(ExternalExecutionModel)))
    return outbox, executions


async def test_enqueue_persists_outbox_and_pending_execution(clean_tables, uow_factory) -> None:
    from personal_pm_api.execution.outbox import ExternalCommand, enqueue_external_command

    ws = await _seed_workspace_id(uow_factory)
    command = make_command(ws)

    async with uow_factory() as uow:
        record = await enqueue_external_command(uow, ExternalCommand(**command))
        await uow.commit()

    assert record.idempotency_key == "idem-ob-1"
    outbox_count, execution_count = await _counts(uow_factory)
    assert (outbox_count, execution_count) == (1, 1)


async def test_crash_before_commit_writes_nothing(clean_tables, uow_factory) -> None:
    from personal_pm_api.execution.outbox import ExternalCommand, enqueue_external_command

    ws = await _seed_workspace_id(uow_factory)
    command = make_command(ws, key="idem-crash")

    with pytest.raises(RuntimeError):
        async with uow_factory() as uow:
            await enqueue_external_command(uow, ExternalCommand(**command))
            raise RuntimeError("crash before commit")

    outbox_count, execution_count = await _counts(uow_factory)
    assert (outbox_count, execution_count) == (0, 0)


async def test_duplicate_idempotency_key_is_rejected(clean_tables, uow_factory) -> None:
    from personal_pm_api.execution.outbox import ExternalCommand, enqueue_external_command

    ws = await _seed_workspace_id(uow_factory)
    command = make_command(ws, key="idem-dup")

    async with uow_factory() as uow:
        await enqueue_external_command(uow, ExternalCommand(**command))
        await uow.commit()

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        async with uow_factory() as uow:
            await enqueue_external_command(uow, ExternalCommand(**command))


async def test_execution_requires_verified_success_shape(clean_tables, uow_factory) -> None:
    """A Succeeded execution without external_id violates the verified invariant."""
    from personal_pm_api.execution.models import ExternalExecutionModel
    from personal_pm_api.execution.outbox import ExternalCommand, enqueue_external_command
    from sqlalchemy.exc import IntegrityError

    ws = await _seed_workspace_id(uow_factory)
    command = make_command(ws, key="idem-verify")

    async with uow_factory() as uow:
        record = await enqueue_external_command(uow, ExternalCommand(**command))
        bad = ExternalExecutionModel(
            outbox_event_id=record.id,
            idempotency_key=record.idempotency_key,
            provider="google_calendar",
            external_id=None,
            result_status="Succeeded",
            verified=True,
            executed_at=datetime.now(UTC),
        )
        uow.typed_session.add(bad)
        with pytest.raises(IntegrityError):
            await uow.typed_session.flush()
