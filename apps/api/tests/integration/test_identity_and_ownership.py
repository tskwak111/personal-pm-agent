from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def api(clean_tables, database_url_session: str) -> AsyncIterator[dict[str, Any]]:
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

    async with factory() as session:
        ids: dict[str, Any] = {}
        for label in ("a", "b"):
            user_id = uuid4()
            workspace_id = uuid4()
            raw_token = secrets.token_urlsafe(32)
            from personal_pm_api.identity.models import UserSessionModel
            from personal_pm_api.identity.session import hash_session_token
            from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

            session.add(UserModel(id=user_id, email=f"{label}@example.com", display_name=label))
            session.add(WorkspaceModel(id=workspace_id, owner_user_id=user_id, name=f"ws-{label}"))
            session.add(
                UserSessionModel(
                    id=uuid4(),
                    user_id=user_id,
                    token_hash=hash_session_token(raw_token),
                    expires_at=datetime.now(UTC) + timedelta(hours=8),
                )
            )
            ids[f"user_{label}"] = str(user_id)
            ids[f"workspace_{label}"] = str(workspace_id)
            ids[f"token_{label}"] = raw_token
            # Flush per label so FK targets exist before dependent inserts.
            await session.flush()
        await session.commit()

    # B owns a workstream and one ready task.
    from personal_pm_api.planning.models import TaskModel, WorkstreamModel

    workstream_b_id = uuid4()
    task_b_id = uuid4()
    async with factory() as session:
        session.add(
            WorkstreamModel(
                id=workstream_b_id,
                workspace_id=UUID(ids["workspace_b"]),
                area_id=None,
                name="B의 수업",
                importance="normal",
                status="active",
                version=1,
            )
        )
        await session.flush()
        session.add(
            TaskModel(
                id=task_b_id,
                workspace_id=UUID(ids["workspace_b"]),
                workstream_id=workstream_b_id,
                milestone_id=None,
                title="B의 작업",
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
        )
        await session.commit()

    ids["app"] = app
    ids["task_b"] = str(task_b_id)
    ids["engine"] = engine

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://testserver")
    try:
        yield {**ids, "client": client}
    finally:
        await client.aclose()
        await engine.dispose()
        await reset_engine()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_missing_session_is_unauthorized(api: dict) -> None:
    client: AsyncClient = api["client"]
    response = await client.get("/api/v1/workstreams")
    assert response.status_code == 401


async def test_cookie_only_request_is_unauthorized(api: dict) -> None:
    client: AsyncClient = api["client"]
    response = await client.get(
        "/api/v1/workstreams",
        headers={"Cookie": f"session={api['token_a']}"},
    )
    assert response.status_code == 401


async def test_cross_workspace_object_is_not_disclosed(api: dict) -> None:
    client: AsyncClient = api["client"]
    task_b = api["task_b"]

    hidden = await client.get(f"/api/v1/tasks/{task_b}", headers=_auth(api["token_a"]))
    assert hidden.status_code == 404

    visible = await client.get(f"/api/v1/tasks/{task_b}", headers=_auth(api["token_b"]))
    assert visible.status_code == 200
    assert visible.json()["title"] == "B의 작업"

    missing = await client.get(f"/api/v1/tasks/{uuid4()}", headers=_auth(api["token_b"]))
    assert missing.status_code == 404


async def test_workstreams_are_scoped_to_own_workspace(api: dict) -> None:
    client: AsyncClient = api["client"]
    response = await client.get("/api/v1/workstreams", headers=_auth(api["token_b"]))
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["name"] for item in items] == ["B의 수업"]


async def test_seeded_test_session_provisions_a_complete_owned_browser_fixture(api: dict) -> None:
    client: AsyncClient = api["client"]
    session = await client.post(
        "/api/v1/identity/test-session",
        json={"email": "browser-e2e@example.com", "seed_demo": True},
    )

    assert session.status_code == 200
    headers = _auth(session.json()["token"])
    today = await client.get("/api/v1/today", headers=headers)
    inbox = await client.get("/api/v1/inbox", headers=headers)
    review = await client.get("/api/v1/review", headers=headers)

    assert today.status_code == 200
    assert today.json()["core_outcome"]["title"] == "오늘의 핵심 작업"
    assert inbox.json()["candidates"][0]["source_text"] == "금요일까지 제안서 초안"
    assert review.json()["pending_proposals"][0]["status"] == "pending"

    task = today.json()["core_outcome"]
    transitioned = await client.post(
        f"/api/v1/tasks/{task['id']}/transition",
        headers=headers,
        json={"expected_version": task["version"], "target_status": "in_progress"},
    )
    reset = await client.post("/api/v1/identity/test-reset", headers=headers)
    restored = await client.get("/api/v1/today", headers=headers)

    assert transitioned.status_code == 200
    assert reset.json() == {"seeded": True}
    assert restored.json()["core_outcome"]["status"] == "ready"


async def test_production_app_hides_test_identity_routes(api: dict) -> None:
    from personal_pm_api.main import create_app
    from personal_pm_api.security.rate_limit import RateLimiter
    from personal_pm_api.settings import ApiSettings

    app = create_app(
        ApiSettings(
            environment="production",
            database_url="postgresql+asyncpg://pma:secret@database.internal/pma",
            s3_endpoint="https://objects.internal",
            s3_access_key_id="production-key",
            s3_secret_access_key="production-secret",
            redis_url="rediss://redis.internal/0",
        ),
        rate_limiter=RateLimiter(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        session = await client.post(
            "/api/v1/identity/test-session",
            json={"email": "should-not-exist@example.com"},
        )
        reset = await client.post("/api/v1/identity/test-reset")

    assert session.status_code == 404
    assert reset.status_code == 404
