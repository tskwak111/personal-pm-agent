from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def router_env(clean_tables, database_url_session: str) -> AsyncIterator[dict[str, Any]]:
    from personal_pm_api.main import create_app
    from personal_pm_api.shared.db import reset_engine
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    app = create_app()
    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    ids: dict[str, Any] = {"factory": factory}

    async with factory() as session:
        from personal_pm_api.approvals.models import ProposalModel
        from personal_pm_api.identity.models import UserSessionModel
        from personal_pm_api.identity.session import hash_session_token
        from personal_pm_api.planning.models import TaskModel, WorkstreamModel
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        for label in ("a", "b"):
            token = secrets.token_urlsafe(32)
            user = UserModel(email=f"approval-{label}@example.com", display_name=label)
            session.add(user)
            await session.flush()
            workspace = WorkspaceModel(owner_user_id=user.id, name=f"approval-{label}")
            session.add(workspace)
            session.add(
                UserSessionModel(
                    user_id=user.id,
                    token_hash=hash_session_token(token),
                    expires_at=datetime.now(UTC) + timedelta(hours=1),
                )
            )
            await session.flush()
            ids[f"token_{label}"] = token
            ids[f"workspace_{label}"] = workspace.id

        workstream = WorkstreamModel(
            workspace_id=ids["workspace_a"],
            area_id=None,
            name="approval",
            importance="normal",
            status="active",
            version=1,
        )
        session.add(workstream)
        await session.flush()
        task = TaskModel(
            workspace_id=ids["workspace_a"],
            workstream_id=workstream.id,
            milestone_id=None,
            title="원본 제목",
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
        change = {
            "type": "UPDATE_TASK_TITLE",
            "target_type": "task",
            "target_id": str(task.id),
            "target_version": task.version,
            "values": {"title": "승인된 제목"},
        }
        proposal = ProposalModel(
            id=uuid4(),
            workspace_id=ids["workspace_a"],
            kind="TASK_UPDATE",
            approval_level="CONFIRM",
            payload_hash=hashlib.sha256(
                json.dumps(
                    [change], sort_keys=True, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest(),
            targets_json=[change],
            status="pending",
            version=2,
        )
        session.add(proposal)
        await session.commit()
        ids.update(task=task.id, proposal=proposal.id, proposal_version=proposal.version)

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    ids["client"] = client
    try:
        yield ids
    finally:
        await client.aclose()
        await engine.dispose()
        await reset_engine()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_approve_executes_and_audits(router_env: dict[str, Any]) -> None:
    from personal_pm_api.audit.models import AuditEventModel
    from sqlalchemy import func, select

    response = await router_env["client"].post(
        f"/api/v1/proposals/{router_env['proposal']}/approve",
        headers=_auth(router_env["token_a"]),
        json={"decision": "approve", "expected_version": router_env["proposal_version"]},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "EXECUTED"
    async with router_env["factory"]() as session:
        audits = int(await session.scalar(select(func.count()).select_from(AuditEventModel)))
    assert audits == 1


async def test_wrong_workspace_is_hidden(router_env: dict[str, Any]) -> None:
    response = await router_env["client"].post(
        f"/api/v1/proposals/{router_env['proposal']}/approve",
        headers=_auth(router_env["token_b"]),
        json={"decision": "approve", "expected_version": router_env["proposal_version"]},
    )
    assert response.status_code == 404


async def test_stale_proposal_version_is_conflict(router_env: dict[str, Any]) -> None:
    response = await router_env["client"].post(
        f"/api/v1/proposals/{router_env['proposal']}/approve",
        headers=_auth(router_env["token_a"]),
        json={"decision": "approve", "expected_version": 1},
    )
    assert response.status_code == 409


async def test_changed_target_supersedes_proposal(router_env: dict[str, Any]) -> None:
    from personal_pm_api.planning.models import TaskModel

    async with router_env["factory"]() as session:
        task = await session.get(TaskModel, router_env["task"])
        assert task is not None
        task.version += 1
        await session.commit()
    response = await router_env["client"].post(
        f"/api/v1/proposals/{router_env['proposal']}/approve",
        headers=_auth(router_env["token_a"]),
        json={"decision": "approve", "expected_version": router_env["proposal_version"]},
    )
    assert response.status_code == 409
    assert response.json()["status"] == "SUPERSEDED"


async def test_reject_decision_is_executed(router_env: dict[str, Any]) -> None:
    response = await router_env["client"].post(
        f"/api/v1/proposals/{router_env['proposal']}/approve",
        headers=_auth(router_env["token_a"]),
        json={"decision": "reject", "expected_version": router_env["proposal_version"]},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


async def test_unknown_decision_is_validation_error(router_env: dict[str, Any]) -> None:
    response = await router_env["client"].post(
        f"/api/v1/proposals/{router_env['proposal']}/approve",
        headers=_auth(router_env["token_a"]),
        json={"decision": "later", "expected_version": router_env["proposal_version"]},
    )
    assert response.status_code == 422
