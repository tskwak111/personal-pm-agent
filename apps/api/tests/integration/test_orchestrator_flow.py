from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest_asyncio


@pytest_asyncio.fixture
async def orch_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {}
    async with factory() as session:
        from personal_pm_api.approvals.models import ProposalModel
        from personal_pm_api.planning.models import TaskModel, WorkstreamModel
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        user = UserModel(email="orch@example.com", display_name="O")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-orch")
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
            title="집중 작업",
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

        payload = {
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
            payload_hash=__import__("hashlib").sha256(json_dumps(payload).encode()).hexdigest(),
            targets_json=[payload],
            status="approved",
            version=1,
        )
        session.add(proposal)
        await session.commit()

        ids["workspace"] = str(workspace.id)
        ids["proposal"] = str(proposal.id)

    from personal_pm_api.agent.orchestrator import AgentOrchestrator

    class Actor:
        def __init__(self, wid: str) -> None:
            self.user_id = "00000000-0000-0000-0000-000000000001"
            self.workspace_id = wid

    ids["factory"] = factory
    ids["actor"] = Actor(ids["workspace"])
    ids["orchestrator"] = AgentOrchestrator(factory)
    yield ids
    await engine.dispose()


def json_dumps(payload: dict[str, object]) -> str:
    import json

    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _now_iso() -> str:
    return (datetime.now(UTC) + timedelta(hours=2)).isoformat()


async def test_mutating_operation_cannot_act_before_authorization(
    orch_env: dict[str, Any],
) -> None:
    orchestrator: Any = orch_env["orchestrator"]
    actor: Any = orch_env["actor"]

    result = await orchestrator.handle(
        actor,
        text=f"집중 블록 만들어줘 proposal:{orch_env['proposal']}",
        proposed_external_action={"proposal_id": orch_env["proposal"]},
    )
    steps = [event.step for event in result.events]
    assert steps.index("AUTHORIZE") < steps.index("ACT")
    assert result.external_action_executed is False


async def test_failed_external_verification_is_reported_as_failed(
    orch_env: dict[str, Any],
) -> None:
    from personal_pm_worker.calendar.repository import PermanentFailureError

    orchestrator: Any = orch_env["orchestrator"]
    actor: Any = orch_env["actor"]

    class FailingExecutor:
        calls = 0

        async def execute(self, proposal_id: str) -> str:
            type(self).calls += 1
            raise PermanentFailureError("provider rejected")

    orchestrator.set_external_executor(FailingExecutor())
    result = await orchestrator.handle(
        actor,
        text="실행해줘",
        approved_proposal_id=orch_env["proposal"],
    )
    assert result.status == "FAILED"
    assert result.user_message_code == "EXTERNAL_EXECUTION_FAILED"


async def test_missing_external_executor_never_reports_success(
    orch_env: dict[str, Any],
) -> None:
    from personal_pm_api.agent.orchestrator import StepEvent

    result = await orch_env["orchestrator"].handle(
        orch_env["actor"],
        text="실행해줘",
        approved_proposal_id=orch_env["proposal"],
    )

    assert result.status == "FAILED"
    assert result.external_action_executed is False
    assert result.user_message_code == "EXTERNAL_EXECUTOR_UNAVAILABLE"
    assert result.events[-1] == StepEvent(step="VERIFY", status="FAILED")


async def test_read_only_operation_skips_authorize_and_act(
    orch_env: dict[str, Any],
) -> None:
    orchestrator: Any = orch_env["orchestrator"]
    actor: Any = orch_env["actor"]

    result = await orchestrator.handle(actor, text="오늘 일정이 뭐야?")
    steps = [event.step for event in result.events]
    assert "ACT" not in steps
    assert result.status == "SUCCEEDED"


async def test_ambiguous_language_never_executes(orch_env: dict[str, Any]) -> None:
    orchestrator: Any = orch_env["orchestrator"]
    actor: Any = orch_env["actor"]

    result = await orchestrator.handle(actor, text="미루면 어떨까?")
    assert result.mutated is False
