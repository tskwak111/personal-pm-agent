from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

import hashlib
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest_asyncio


@pytest_asyncio.fixture
async def focus_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {}
    async with factory() as session:
        from personal_pm_api.approvals.models import ProposalModel
        from personal_pm_api.planning.models import TaskModel, WorkstreamModel
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        user = UserModel(email="focus@example.com", display_name="F")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-focus")
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
            title="보고서 작성",
            status="ready",
            deadline_date=None,
            deadline_at=None,
            deadline_time_known=False,
            start_after=None,
            base_duration_minutes=90,
            safety_duration_minutes=120,
            remaining_base_minutes=90,
            remaining_safety_minutes=120,
            uncertainty="medium",
            splittable=True,
            min_chunk_minutes=30,
            pinned=False,
            waiting_reason=None,
            version=1,
        )
        session.add(task)
        await session.flush()

        proposal_payload = {
            "task_id": str(task.id),
            "target_version": task.version,
            "start_at": "2026-09-03T01:00:00Z",
            "duration_minutes": 90,
        }
        proposal = ProposalModel(
            id=uuid4(),
            workspace_id=workspace.id,
            kind="FOCUS_BLOCK_CREATE",
            approval_level="CONFIRM",
            payload_hash=hashlib.sha256(
                json.dumps(proposal_payload, sort_keys=True).encode()
            ).hexdigest(),
            targets_json=[proposal_payload],
            status="pending",
            version=3,
        )
        session.add(proposal)
        await session.commit()

        ids["task"] = str(task.id)
        ids["task_version"] = task.version
        ids["proposal"] = str(proposal.id)
        ids["proposal_version"] = proposal.version
        ids["workspace"] = str(workspace.id)

    from personal_pm_api.calendar.focus_blocks import FocusBlockApprovalService

    ids["factory"] = factory
    ids["service"] = FocusBlockApprovalService(factory)
    yield ids
    await engine.dispose()


class _Actor:
    def __init__(self, wid: str) -> None:
        self.user_id = "00000000-0000-0000-0000-00000000000f"
        self.workspace_id = wid


async def test_focus_block_creation_requires_approval(focus_env: dict[str, Any]) -> None:
    service: Any = focus_env["service"]
    actor = _Actor(focus_env["workspace"])
    result = await service.propose(
        actor,
        task_id=focus_env["task"],
        expected_task_version=focus_env["task_version"],
        start_at=datetime(2026, 9, 4, 1, 0, tzinfo=UTC),
        duration_minutes=90,
    )
    assert result.status == "PENDING"
    assert result.approval_level in ("CONFIRM", "RECONFIRM")


async def test_stale_task_version_invalidates_approval(focus_env: dict[str, Any]) -> None:
    service: Any = focus_env["service"]
    actor = _Actor(focus_env["workspace"])
    # Approve while the recorded target version matches.
    approved = await service.approve(
        actor,
        proposal_id=focus_env["proposal"],
        proposal_version=focus_env["proposal_version"],
    )
    assert approved.status == "APPROVED"

    # Now bump the task version behind the proposal's back → superseded.
    async with focus_env["factory"]() as session:
        from personal_pm_api.planning.models import TaskModel
        from sqlalchemy import select

        model = (
            (await session.execute(select(TaskModel).where(TaskModel.id == focus_env["task"])))
            .scalars()
            .one()
        )
        model.version += 1
        await session.commit()

    result = await service.execute_approved(actor, proposal_id=focus_env["proposal"])
    assert result.status == "SUPERSEDED"
    assert result.reason == "TARGET_VERSION_CHANGED"


async def test_execute_approved_enqueues_outbox_command(focus_env: dict[str, Any]) -> None:
    from personal_pm_api.execution.models import OutboxEventModel
    from sqlalchemy import select

    service: Any = focus_env["service"]
    actor = _Actor(focus_env["workspace"])
    approved = await service.approve(
        actor,
        proposal_id=focus_env["proposal"],
        proposal_version=focus_env["proposal_version"],
    )
    assert approved.status == "APPROVED"

    outcome = await service.execute_approved(actor, proposal_id=focus_env["proposal"])
    assert outcome.status == "APPROVED"
    assert outcome.outbox_event_id is not None

    async with focus_env["factory"]() as session:
        record = (
            (
                await session.execute(
                    select(OutboxEventModel).where(OutboxEventModel.id == outcome.outbox_event_id)
                )
            )
            .scalars()
            .one()
        )
    assert record.command_type == "CREATE_FOCUS_BLOCK"
