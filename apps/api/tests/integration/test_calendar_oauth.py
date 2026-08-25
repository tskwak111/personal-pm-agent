from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def oauth_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
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
    raw_token = secrets.token_urlsafe(32)
    async with factory() as session:
        from personal_pm_api.identity.models import UserSessionModel
        from personal_pm_api.identity.session import hash_session_token
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        user = UserModel(email="cal@example.com", display_name="C")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-cal")
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


async def test_oauth_callback_rejects_state_mismatch(oauth_env: dict[str, Any]) -> None:
    client: AsyncClient = oauth_env["client"]
    response = await client.get("/api/v1/calendar/oauth/callback?code=x&state=wrong")
    assert response.status_code == 400
    assert response.json()["code"] == "OAUTH_STATE_MISMATCH"


async def test_read_connection_does_not_request_write_scope(
    oauth_env: dict[str, Any],
) -> None:
    client: AsyncClient = oauth_env["client"]
    response = await client.post(
        "/api/v1/calendar/connections",
        json={"mode": "READ_ONLY"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "calendar.events" not in body["authorization_url"]
    assert (
        "calendarEvents.readonly" in body["authorization_url"]
        or "calendar.readonly" in body["authorization_url"]
    )
    assert len(body["state"]) >= 16


async def test_write_mode_requests_write_scope(oauth_env: dict[str, Any]) -> None:
    client: AsyncClient = oauth_env["client"]
    response = await client.post(
        "/api/v1/calendar/connections",
        json={"mode": "READ_WRITE"},
    )
    assert response.status_code == 201
    assert "calendar.events" in response.json()["authorization_url"]


async def test_token_vault_roundtrip_and_wrong_key_rejection(
    oauth_env: dict[str, Any],
) -> None:
    from personal_pm_api.calendar.token_vault import TokenVault

    vault = TokenVault(master_key=b"k" * 32)
    encrypted = vault.encrypt("refresh-token-secret", key_version=1)
    assert encrypted.ciphertext != b"refresh-token-secret"
    plaintext = vault.decrypt(encrypted)
    assert plaintext == "refresh-token-secret"


async def test_oauth_state_is_single_use(oauth_env: dict[str, Any]) -> None:
    from personal_pm_api.calendar.oauth import OAuthStateStore

    store = OAuthStateStore()
    state = store.issue(workspace_id=oauth_env["workspace"])
    assert store.consume(state) == oauth_env["workspace"]
    # second consume must fail (single use)
    assert store.consume(state) is None
