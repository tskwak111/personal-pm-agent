"""Calendar connection endpoints with verified OAuth state and tokens."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.responses import Response

from personal_pm_api.calendar.connections import persist_verified_connection
from personal_pm_api.calendar.oauth import (
    OAuthExchangeError,
    OAuthStateStore,
    build_authorization_url,
    configured_scopes,
    exchange_authorization_code,
    provider_is_configured,
)
from personal_pm_api.identity.router import current_actor
from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.settings import ApiSettings
from personal_pm_api.shared.db import database_session

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])
_state_store = OAuthStateStore()


class CreateConnectionRequest(BaseModel):
    mode: str = "READ_ONLY"


class ConnectionResponse(BaseModel):
    authorization_url: str
    state: str
    mode: str


def _settings(request: Request) -> ApiSettings:
    settings = getattr(request.app.state, "settings", None)
    return settings if isinstance(settings, ApiSettings) else ApiSettings()


@router.post("/connections", response_model=ConnectionResponse, status_code=201)
async def create_connection(
    request: CreateConnectionRequest,
    actor: Annotated[CurrentActor, Depends(current_actor)],
    settings: Annotated[ApiSettings, Depends(_settings)],
) -> ConnectionResponse | Response:
    if request.mode not in {"READ_ONLY", "READ_WRITE"}:
        from personal_pm_api.shared.errors import DomainRuleError

        raise DomainRuleError("UNSUPPORTED_CONNECTION_MODE", f"mode {request.mode}")
    if not provider_is_configured(settings):
        return JSONResponse(
            status_code=503,
            content={"code": "OAUTH_PROVIDER_NOT_CONFIGURED"},
        )
    now = datetime.now(UTC)
    state = _state_store.issue(
        workspace_id=str(actor.workspace_id),
        mode=request.mode,
        now_utc=now,
    )
    state_value = _state_store.peek(state)
    assert state_value is not None
    url = build_authorization_url(
        mode=request.mode,
        state=state,
        code_verifier=state_value.code_verifier,
        settings=settings,
    )
    return ConnectionResponse(authorization_url=url, state=state, mode=request.mode)


@router.get("/oauth/callback")
async def oauth_callback(
    settings: Annotated[ApiSettings, Depends(_settings)],
    code: str | None = None,
    state: str | None = None,
) -> JSONResponse:
    if not state:
        return JSONResponse(status_code=400, content={"code": "OAUTH_STATE_MISMATCH"})
    if not code:
        return JSONResponse(status_code=400, content={"code": "OAUTH_CODE_MISSING"})
    state_value = _state_store.consume(state, now_utc=datetime.now(UTC))
    if state_value is None:
        return JSONResponse(status_code=400, content={"code": "OAUTH_STATE_MISMATCH"})
    if not provider_is_configured(settings):
        return JSONResponse(
            status_code=503,
            content={"code": "OAUTH_PROVIDER_NOT_CONFIGURED"},
        )
    try:
        tokens = await exchange_authorization_code(
            code,
            settings.google_oauth_redirect_uri,
            settings,
            code_verifier=state_value.code_verifier,
        )
    except OAuthExchangeError:
        return JSONResponse(status_code=502, content={"code": "OAUTH_EXCHANGE_FAILED"})
    required_scopes = set(configured_scopes(state_value.mode))
    if not required_scopes.issubset(tokens.scopes):
        return JSONResponse(status_code=502, content={"code": "OAUTH_SCOPE_MISMATCH"})

    try:
        async with database_session() as session:
            connection = await persist_verified_connection(
                session,
                workspace_id=UUID(state_value.workspace_id),
                mode=state_value.mode,
                tokens=tokens,
                settings=settings,
            )
            await session.commit()
    except ValueError:
        return JSONResponse(
            status_code=503,
            content={"code": "OAUTH_PROVIDER_NOT_CONFIGURED"},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "CONNECTED", "connection_id": str(connection.id)},
    )


__all__ = ["router"]
