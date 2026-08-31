from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

import asyncio
import hashlib
import json
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
            payload_hash=hashlib.sha256(
                json.dumps(
                    [proposed_change], sort_keys=True, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest(),
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
        ids["user"] = str(user.id)

    from personal_pm_api.approvals.service import ApprovalService

    class Actor:
        def __init__(self, wid: str) -> None:
            self.user_id = ids["user"]
            self.workspace_id = wid
            self.session_id = "00000000-0000-0000-0000-000000000003"

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


async def test_payload_hash_mismatch_never_executes(approval_env: dict[str, Any]) -> None:
    from personal_pm_api.approvals.models import ProposalModel
    from personal_pm_api.planning.models import TaskModel

    async with approval_env["factory"]() as session:
        proposal = await session.get(ProposalModel, approval_env["proposal"])
        assert proposal is not None
        tampered = dict(proposal.targets_json[0])
        tampered["values"] = {"title": "변조된 제목"}
        proposal.targets_json = [tampered]
        await session.commit()

    result = await approval_env["service"].approve(
        approval_env["actor"],
        proposal_id=approval_env["proposal"],
        expected_version=approval_env["proposal_version"],
    )

    assert result.status == "CONFLICT"
    async with approval_env["factory"]() as session:
        task = await session.get(TaskModel, approval_env["task"])
        assert task is not None
        assert task.title == "대상 작업"


async def test_execution_and_audit_commit_together(approval_env: dict[str, Any]) -> None:
    from personal_pm_api.audit.models import AuditEventModel
    from sqlalchemy import func, select

    result = await approval_env["service"].approve(
        approval_env["actor"],
        proposal_id=approval_env["proposal"],
        expected_version=approval_env["proposal_version"],
    )
    assert result.status == "EXECUTED"

    async with approval_env["factory"]() as session:
        count = int(await session.scalar(select(func.count()).select_from(AuditEventModel)))
    assert count == 1


async def test_audit_failure_rolls_back_execution(
    approval_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from personal_pm_api.approvals.models import ProposalModel
    from personal_pm_api.audit.repository import AuditRepository
    from personal_pm_api.planning.models import TaskModel

    async def fail_audit(*args: object, **kwargs: object) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditRepository, "append", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        await approval_env["service"].approve(
            approval_env["actor"],
            proposal_id=approval_env["proposal"],
            expected_version=approval_env["proposal_version"],
        )

    async with approval_env["factory"]() as session:
        task = await session.get(TaskModel, approval_env["task"])
        proposal = await session.get(ProposalModel, approval_env["proposal"])
        assert task is not None and proposal is not None
        assert task.title == "대상 작업"
        assert proposal.status == "pending"


async def test_concurrent_decisions_execute_once(approval_env: dict[str, Any]) -> None:
    from personal_pm_api.approvals.models import ApprovalModel
    from personal_pm_api.audit.models import AuditEventModel
    from sqlalchemy import func, select

    async def approve() -> Any:
        return await approval_env["service"].approve(
            approval_env["actor"],
            proposal_id=approval_env["proposal"],
            expected_version=approval_env["proposal_version"],
        )

    outcomes = await asyncio.gather(approve(), approve())

    assert sorted(outcome.status for outcome in outcomes) == ["CONFLICT", "EXECUTED"]
    async with approval_env["factory"]() as session:
        approvals = int(await session.scalar(select(func.count()).select_from(ApprovalModel)))
        audits = int(await session.scalar(select(func.count()).select_from(AuditEventModel)))
    assert (approvals, audits) == (1, 1)
