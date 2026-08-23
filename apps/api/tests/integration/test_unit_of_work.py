from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select


async def _count(model) -> int:
    from personal_pm_api.shared.db import session_factory

    factory = session_factory()
    async with factory() as session:
        return int(await session.scalar(select(func.count()).select_from(model)))


async def _seed_workspace() -> object:
    from personal_pm_api.shared.db import session_factory
    from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

    factory = session_factory()
    async with factory() as session:
        user = UserModel(email="uow@example.com", display_name="UoW")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="uow-ws")
        session.add(workspace)
        await session.commit()
        return workspace.id


async def test_unit_of_work_commits_domain_and_audit_atomically(clean_tables, uow_factory) -> None:
    from personal_pm_api.audit.models import AuditEventModel
    from personal_pm_api.planning.models import WorkstreamModel
    from personal_pm_planner.domain.identifiers import TaskId

    workspace_id = await _seed_workspace()
    trace_id = str(TaskId(__import__("uuid").UUID(int=1)))

    async with uow_factory() as uow:
        workstream = await uow.workstreams.create(
            workspace_id=workspace_id,
            name="데이터베이스 수업",
            importance="protected",
            status="active",
        )
        await uow.audit.append(
            workspace_id=workspace_id,
            actor_user_id=None,
            entity_kind="workstream",
            entity_id=str(workstream.id),
            reason="seeded by uow test",
            rule_basis=("SEED-1",),
            trace_id=trace_id,
            reversible=True,
            occurred_at=datetime.now(UTC),
            after_state={"name": "데이터베이스 수업"},
        )
        await uow.commit()

    assert await _count(WorkstreamModel) == 1
    assert await _count(AuditEventModel) == 1


async def test_unit_of_work_exception_rolls_back_both(clean_tables, uow_factory) -> None:
    from personal_pm_api.planning.models import WorkstreamModel

    workspace_id = await _seed_workspace()

    with pytest.raises(RuntimeError):
        async with uow_factory() as uow:
            await uow.workstreams.create(
                workspace_id=workspace_id,
                name="롤백 대상",
                importance="normal",
                status="active",
            )
            raise RuntimeError("abort before commit")

    assert await _count(WorkstreamModel) == 0
