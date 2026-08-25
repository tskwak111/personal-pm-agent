from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import pytest_asyncio


@pytest_asyncio.fixture
async def approval_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {}
    async with factory() as session:
        from personal_pm_api.approvals.models import ProposalModel
        from personal_pm_api.planning.models import TaskModel, WorkstreamModel
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        user = UserModel(email="appr@example.com", display_name="P")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-appr")
        session.add(workspace)
        await session.flush()
        workstream = WorkstreamModel(
            workspace_id=workspace.id,
            area_id=None,
            name="ws",
            importance="normal",
            status="active",
            version=1,
        )
        session.add(workstream)
        await session.flush()
        task = TaskModel(
            workspace_id=workspace.id,
            workstream_id=workstream.id,
            milestone_id=None,
            title="대상 작업",
            status="ready",
            deadline_date=None,
            deadline_at=None,
            deadline_time_known=False,
            start_after=None,
            base_duration_minutes=60,
            safety_duration_minutes=90,
            remaining_base_minutes=60,
            remaining_safety_minutes=90,
            uncertainty="medium",
            splittable=True,
            min_chunk_minutes=30,
            pinned=False,
            waiting_reason=None,
            version=1,
        )
        session.add(task)
        await session.flush()

        proposed_change = {
            "type": "UPDATE_TASK_TITLE",
            "target_type": "task",
            "target_id": str(task.id),
            "target_version": task.version,
            "values": {"title": "수정된 제목"},
        }
        proposal = ProposalModel(
            id=uuid4(),
            workspace_id=workspace.id,
            kind="TASK_UPDATE",
            approval_level="CONFIRM",
            payload_hash=__import__("hashlib").sha256(b"x").hexdigest(),
            targets_json=[proposed_change],
            status="pending",
            version=2,
        )
        session.add(proposal)
        await session.commit()

        ids["task"] = str(task.id)
        ids["proposal"] = str(proposal.id)
        ids["proposal_version"] = proposal.version
        ids["workspace"] = str(workspace.id)

    from personal_pm_api.approvals.service import ApprovalService

    class Actor:
        def __init__(self, wid: str) -> None:
            self.user_id = "00000000-0000-0000-0000-000000000002"
            self.workspace_id = wid

    ids["factory"] = factory
    ids["actor"] = Actor(ids["workspace"])
    ids["service"] = ApprovalService(factory)
    yield ids
    await engine.dispose()


async def test_approval_executes_exact_proposed_change(approval_env: dict[str, Any]) -> None:
    service: Any = approval_env["service"]
    actor: Any = approval_env["actor"]
    result = await service.approve(
        actor,
        proposal_id=approval_env["proposal"],
        expected_version=approval_env["proposal_version"],
    )
    assert result.status == "EXECUTED"
    assert result.executed_change is not None
    assert result.executed_change.get("title") == "수정된 제목"


async def test_changed_target_supersedes_old_proposal(approval_env: dict[str, Any]) -> None:
    service: Any = approval_env["service"]
    actor: Any = approval_env["actor"]

    # Mutate the target behind the proposal's back.
    async with approval_env["factory"]() as session:
        from personal_pm_api.planning.models import TaskModel
        from sqlalchemy import select

        task = (
            (await session.execute(select(TaskModel).where(TaskModel.id == approval_env["task"])))
            .scalars()
            .one()
        )
        task.version += 1
        await session.commit()

    result = await service.approve(
        actor,
        proposal_id=approval_env["proposal"],
        expected_version=approval_env["proposal_version"],
    )
    assert result.status == "SUPERSEDED"


async def test_wrong_proposal_version_is_conflict(approval_env: dict[str, Any]) -> None:
    service: Any = approval_env["service"]
    actor: Any = approval_env["actor"]
    result = await service.approve(actor, proposal_id=approval_env["proposal"], expected_version=1)
    assert result.status == "CONFLICT"


async def test_reject_marks_proposal_rejected(approval_env: dict[str, Any]) -> None:
    service: Any = approval_env["service"]
    actor: Any = approval_env["actor"]
    result = await service.reject(
        actor,
        proposal_id=approval_env["proposal"],
        expected_version=approval_env["proposal_version"],
    )
    assert result.status == "REJECTED"
