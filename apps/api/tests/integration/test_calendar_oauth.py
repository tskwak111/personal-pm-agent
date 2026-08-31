from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

import base64
import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def oauth_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from personal_pm_api.main import create_app
    from personal_pm_api.settings import ApiSettings
    from personal_pm_api.shared.db import reset_engine
    from pydantic import SecretStr
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    settings = ApiSettings(
        environment="test",
        google_oauth_client_id="test-client",
        google_oauth_client_secret=SecretStr("test-secret"),
        google_oauth_redirect_uri="http://testserver/api/v1/calendar/oauth/callback",
        token_encryption_key=SecretStr(base64.urlsafe_b64encode(b"k" * 32).decode()),
    )
    app = create_app(settings)
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


async def test_authorization_url_uses_pkce(oauth_env: dict[str, Any]) -> None:
    from urllib.parse import parse_qs, urlparse

    response = await oauth_env["client"].post(
        "/api/v1/calendar/connections", json={"mode": "READ_ONLY"}
    )
    query = parse_qs(urlparse(response.json()["authorization_url"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["code_challenge"][0]) >= 43


async def test_oauth_callback_requires_code(oauth_env: dict[str, Any]) -> None:
    initiated = await oauth_env["client"].post(
        "/api/v1/calendar/connections", json={"mode": "READ_ONLY"}
    )
    state = initiated.json()["state"]

    response = await oauth_env["client"].get(f"/api/v1/calendar/oauth/callback?state={state}")

    assert response.status_code == 400
    assert response.json()["code"] == "OAUTH_CODE_MISSING"


async def test_unconfigured_provider_never_reports_connected(
    clean_tables, database_url_session: str
) -> None:
    from personal_pm_api.calendar.router import _state_store
    from personal_pm_api.main import create_app
    from personal_pm_api.settings import ApiSettings
    from personal_pm_api.shared.db import reset_engine

    state = _state_store.issue(
        workspace_id="00000000-0000-0000-0000-000000000001",
        mode="READ_ONLY",
        now_utc=datetime.now(UTC),
    )
    app = create_app(ApiSettings(environment="test", database_url=database_url_session))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(f"/api/v1/calendar/oauth/callback?state={state}&code=test-code")
    await reset_engine()

    assert response.status_code == 503
    assert response.json()["code"] == "OAUTH_PROVIDER_NOT_CONFIGURED"


async def test_verified_tokens_are_encrypted_before_connection(
    oauth_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from personal_pm_api.calendar.connections import CalendarConnectionModel
    from personal_pm_api.calendar.oauth import READ_ONLY_SCOPES, TokenResponse
    from sqlalchemy import select

    async def exchange(*args: object, **kwargs: object) -> TokenResponse:
        return TokenResponse(
            access_token="access-secret",
            refresh_token="refresh-secret",
            expires_at=datetime(2026, 9, 1, 1, tzinfo=UTC),
            scopes=READ_ONLY_SCOPES,
        )

    monkeypatch.setattr("personal_pm_api.calendar.router.exchange_authorization_code", exchange)
    initiated = await oauth_env["client"].post(
        "/api/v1/calendar/connections", json={"mode": "READ_ONLY"}
    )
    response = await oauth_env["client"].get(
        "/api/v1/calendar/oauth/callback",
        params={"state": initiated.json()["state"], "code": "provider-code"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CONNECTED"
    async with oauth_env["factory"]() as session:
        connection = (await session.execute(select(CalendarConnectionModel))).scalar_one()
    assert connection.access_token_ciphertext != b"access-secret"
    assert connection.refresh_token_ciphertext != b"refresh-secret"
    assert connection.status == "CONNECTED"


async def test_rejected_exchange_returns_502(
    oauth_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from personal_pm_api.calendar.oauth import OAuthExchangeError

    async def reject(*args: object, **kwargs: object) -> None:
        raise OAuthExchangeError("provider rejected code")

    monkeypatch.setattr("personal_pm_api.calendar.router.exchange_authorization_code", reject)
    initiated = await oauth_env["client"].post(
        "/api/v1/calendar/connections", json={"mode": "READ_ONLY"}
    )
    response = await oauth_env["client"].get(
        "/api/v1/calendar/oauth/callback",
        params={"state": initiated.json()["state"], "code": "bad-code"},
    )

    assert response.status_code == 502
    assert response.json()["code"] == "OAUTH_EXCHANGE_FAILED"


async def test_incomplete_provider_token_response_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from personal_pm_api.calendar import oauth
    from personal_pm_api.settings import ApiSettings
    from pydantic import SecretStr

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"access_token": "access-only", "expires_in": 3600}

    class Client:
        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr(oauth.httpx, "AsyncClient", lambda **kwargs: Client())
    settings = ApiSettings(
        environment="test",
        google_oauth_client_id="client",
        google_oauth_client_secret=SecretStr("secret"),
    )

    with pytest.raises(oauth.OAuthExchangeError, match="incomplete"):
        await oauth.exchange_authorization_code(
            "code",
            "http://testserver/callback",
            settings,
            code_verifier="v" * 64,
        )


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
    now = datetime(2026, 9, 1, tzinfo=UTC)
    state = store.issue(workspace_id=oauth_env["workspace"], mode="READ_ONLY", now_utc=now)
    consumed = store.consume(state, now_utc=now)
    assert consumed is not None
    assert consumed.workspace_id == oauth_env["workspace"]
    # second consume must fail (single use)
    assert store.consume(state, now_utc=now) is None


async def test_expired_oauth_state_is_rejected(oauth_env: dict[str, Any]) -> None:
    from personal_pm_api.calendar.oauth import OAuthStateStore

    store = OAuthStateStore(ttl=timedelta(minutes=10))
    now = datetime(2026, 9, 1, tzinfo=UTC)
    state = store.issue(workspace_id=oauth_env["workspace"], mode="READ_ONLY", now_utc=now)
    assert store.consume(state, now_utc=now + timedelta(minutes=10)) is None
