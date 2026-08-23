from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest_asyncio.fixture
async def concurrency_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from personal_pm_api.main import create_app
    from personal_pm_api.shared.db import reset_engine
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    app = create_app()
    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {}
    async with factory() as session:
        from personal_pm_api.identity.models import UserSessionModel
        from personal_pm_api.identity.session import hash_session_token
        from personal_pm_api.planning.models import TaskModel, WorkstreamModel
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        raw_token = secrets.token_urlsafe(32)
        user = UserModel(email="concurrency@example.com", display_name="C")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-c")
        session.add(workspace)
        await session.flush()
        workstream = WorkstreamModel(
            workspace_id=workspace.id,
            area_id=None,
            name="동시성 수업",
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
            title="원래 제목",
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
        session.add(
            UserSessionModel(
                user_id=user.id,
                token_hash=hash_session_token(raw_token),
                expires_at=datetime.now(UTC) + timedelta(hours=8),
            )
        )
        await session.commit()

        ids["app"] = app
        ids["engine"] = engine
        ids["token"] = raw_token
        ids["workspace"] = str(workspace.id)
        ids["task"] = str(task.id)

    transport = ASGITransport(app=app)
    client = AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {ids['token']}"},
    )
    try:
        yield {**ids, "client": client}
    finally:
        await client.aclose()
        await engine.dispose()
        await reset_engine()


def _patch_body(expected_version: int, title: str) -> dict[str, Any]:
    return {"expected_version": expected_version, "title": title}


async def test_first_update_with_current_version_succeeds_and_bumps(
    concurrency_env: dict[str, Any],
) -> None:
    client: AsyncClient = concurrency_env["client"]
    task_id = concurrency_env["task"]

    response = await client.patch(f"/api/v1/tasks/{task_id}", json=_patch_body(1, "first"))
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    assert body["title"] == "first"

    fetched = await client.get(f"/api/v1/tasks/{task_id}")
    assert fetched.json()["title"] == "first"
    assert fetched.json()["version"] == 2


async def test_stale_task_update_returns_conflict(concurrency_env: dict[str, Any]) -> None:
    client: AsyncClient = concurrency_env["client"]
    task_id = concurrency_env["task"]

    first = await client.patch(f"/api/v1/tasks/{task_id}", json=_patch_body(1, "first"))
    assert first.status_code == 200

    second = await client.patch(f"/api/v1/tasks/{task_id}", json=_patch_body(1, "second"))
    assert second.status_code == 409
    assert second.json()["code"] == "STALE_OBJECT_VERSION"


async def test_audit_event_recorded_for_accepted_update(
    concurrency_env: dict[str, Any], database_url_session: str
) -> None:
    from personal_pm_api.audit.models import AuditEventModel
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    client: AsyncClient = concurrency_env["client"]
    task_id = concurrency_env["task"]

    accepted = await client.patch(f"/api/v1/tasks/{task_id}", json=_patch_body(1, "first"))
    assert accepted.status_code == 200

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        audits = list((await session.execute(select(AuditEventModel))).scalars())
    await engine.dispose()

    assert len(audits) == 1
    assert audits[0].entity_kind == "task"
    assert audits[0].reason.startswith("task.update")


async def test_idempotency_key_reserve_is_one_shot(
    concurrency_env: dict[str, Any], database_url_session: str
) -> None:
    from personal_pm_api.shared.idempotency import reserve_key
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    workspace_id = UUID(concurrency_env["workspace"])

    async with factory() as session:
        assert await reserve_key(session, "op-key-1", workspace_id) is True
        await session.commit()

    async with factory() as session:
        assert await reserve_key(session, "op-key-1", workspace_id) is False

    await engine.dispose()
