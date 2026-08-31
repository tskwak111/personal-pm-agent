from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select


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
        ids["factory"] = factory

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


async def _source_and_outbox_counts(upload_env: dict[str, Any]) -> tuple[int, int]:
    from personal_pm_api.execution.models import OutboxEventModel
    from personal_pm_api.inbox.models import SourceArtifactModel

    async with upload_env["factory"]() as session:
        sources = int(await session.scalar(select(func.count()).select_from(SourceArtifactModel)))
        outbox = int(await session.scalar(select(func.count()).select_from(OutboxEventModel)))
    return sources, outbox


async def test_executable_disguised_as_pdf_is_rejected_before_persistence(
    upload_env: dict[str, Any],
) -> None:
    client: AsyncClient = upload_env["client"]
    response = await client.post(
        "/api/v1/inbox/sources?filename=notice.pdf",
        content=b"MZ" + b"x" * 64,
        headers={"Content-Type": "application/pdf"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "UPLOAD_REJECTED"
    assert await _source_and_outbox_counts(upload_env) == (0, 0)


async def test_declared_type_must_match_magic_bytes(upload_env: dict[str, Any]) -> None:
    client: AsyncClient = upload_env["client"]
    response = await client.post(
        "/api/v1/inbox/sources?filename=image.pdf",
        content=b"\x89PNG\r\n\x1a\n" + b"x" * 64,
        headers={"Content-Type": "application/pdf"},
    )

    assert response.status_code == 415
    assert response.json()["code"] == "UPLOAD_TYPE_MISMATCH"
    assert await _source_and_outbox_counts(upload_env) == (0, 0)


async def test_valid_raw_pdf_is_scanned_before_metadata_insert(upload_env: dict[str, Any]) -> None:
    client: AsyncClient = upload_env["client"]
    content = b"%PDF-1.7\nvalid test document"
    response = await client.post(
        "/api/v1/inbox/sources?filename=notice.pdf",
        content=content,
        headers={"Content-Type": "application/pdf"},
    )

    assert response.status_code == 201
    assert await _source_and_outbox_counts(upload_env) == (1, 0)


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


async def test_unscanned_metadata_initiation_is_rejected(
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
    assert response.status_code == 410
    assert response.json()["code"] == "UPLOAD_FLOW_REPLACED"
    assert await _source_and_outbox_counts(upload_env) == (0, 0)


async def test_upload_record_is_persisted_and_immutable_source_identity(
    upload_env: dict[str, Any], database_url_session: str
) -> None:
    from personal_pm_api.inbox.models import SourceArtifactModel
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    client: AsyncClient = upload_env["client"]
    content = b"plain UTF-8 notes"
    created = await client.post(
        "/api/v1/inbox/sources?filename=notes.txt",
        content=content,
        headers={"Content-Type": "text/plain; charset=utf-8"},
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
    assert row.size_bytes == len(content)
    assert str(row.workspace_id) == upload_env["workspace"]
    import hashlib

    assert row.sha256 == hashlib.sha256(content).hexdigest()


async def test_path_like_filename_is_rejected_before_persistence(
    upload_env: dict[str, Any],
) -> None:
    client: AsyncClient = upload_env["client"]
    response = await client.post(
        "/api/v1/inbox/sources?filename=../notice.pdf",
        content=b"%PDF-1.7\nvalid",
        headers={"Content-Type": "application/pdf"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SOURCE_FILENAME"
    assert await _source_and_outbox_counts(upload_env) == (0, 0)


async def test_oversized_content_length_is_rejected_before_body_processing(
    upload_env: dict[str, Any],
) -> None:
    from personal_pm_api.security.uploads import MAX_UPLOAD_BYTES

    client: AsyncClient = upload_env["client"]
    response = await client.post(
        "/api/v1/inbox/sources?filename=notice.pdf",
        content=b"%PDF-1.7\nsmall body",
        headers={
            "Content-Type": "application/pdf",
            "Content-Length": str(MAX_UPLOAD_BYTES + 1),
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "UPLOAD_REJECTED"
    assert await _source_and_outbox_counts(upload_env) == (0, 0)
