from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest_asyncio.fixture
async def upload_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
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
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        raw_token = secrets.token_urlsafe(32)
        user = UserModel(email="upload@example.com", display_name="U")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-upload")
        session.add(workspace)
        session.add(
            UserSessionModel(
                user_id=user.id,
                token_hash=hash_session_token(raw_token),
                expires_at=datetime.now(UTC) + timedelta(hours=8),
            )
        )
        await session.commit()
        ids["workspace"] = str(workspace.id)

    transport = ASGITransport(app=app)
    client = AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    try:
        yield {**ids, "client": client}
    finally:
        await client.aclose()
        await engine.dispose()
        await reset_engine()


async def test_upload_rejects_oversized_or_disallowed_file(
    upload_env: dict[str, Any],
) -> None:
    client: AsyncClient = upload_env["client"]
    response = await client.post(
        "/api/v1/source-artifacts/uploads",
        json={
            "filename": "payload.exe",
            "content_type": "application/x-msdownload",
            "size_bytes": 10,
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "UNSUPPORTED_SOURCE_TYPE"


async def test_oversized_file_is_rejected(upload_env: dict[str, Any]) -> None:
    client: AsyncClient = upload_env["client"]
    response = await client.post(
        "/api/v1/source-artifacts/uploads",
        json={
            "filename": "big.pdf",
            "content_type": "application/pdf",
            "size_bytes": 26 * 1024 * 1024,
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "SOURCE_TOO_LARGE"


async def test_source_artifact_key_is_workspace_scoped(
    upload_env: dict[str, Any],
) -> None:
    client: AsyncClient = upload_env["client"]
    response = await client.post(
        "/api/v1/source-artifacts/uploads",
        json={
            "filename": "syllabus.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["storage_key"].startswith("workspaces/")
    assert body["status"] == "NEW"
    assert len(body["id"]) > 0


async def test_upload_record_is_persisted_and_immutable_source_identity(
    upload_env: dict[str, Any], database_url_session: str
) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from personal_pm_api.inbox.models import SourceArtifactModel

    client: AsyncClient = upload_env["client"]
    created = await client.post(
        "/api/v1/source-artifacts/uploads",
        json={
            "filename": "notes.txt",
            "content_type": "text/plain",
            "size_bytes": 2048,
            "sha256": "a" * 64,
        },
    )
    assert created.status_code == 201

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        rows = list((await session.execute(select(SourceArtifactModel))).scalars())
    await engine.dispose()

    assert len(rows) == 1
    row = rows[0]
    assert row.filename == "notes.txt"
    assert row.content_type == "text/plain"
    assert row.size_bytes == 2048
    assert str(row.workspace_id) == upload_env["workspace"]
    assert row.sha256 == "a" * 64
