"""Calendar connection endpoints (least-privilege OAuth)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from personal_pm_api.calendar.oauth import (
    OAuthStateStore,
    build_authorization_url,
)
from personal_pm_api.identity.router import current_actor
from personal_pm_api.identity.session import CurrentActor

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])

_state_store = OAuthStateStore()


class CreateConnectionRequest(BaseModel):
    mode: str = "READ_ONLY"


class ConnectionResponse(BaseModel):
    authorization_url: str
    state: str
    mode: str


@router.post("/connections", response_model=ConnectionResponse, status_code=201)
async def create_connection(
    request: CreateConnectionRequest,
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> ConnectionResponse:
    if request.mode not in ("READ_ONLY", "READ_WRITE"):
        raise DomainRuleError("UNSUPPORTED_CONNECTION_MODE", f"mode {request.mode}")
    state = _state_store.issue(workspace_id=str(actor.workspace_id))
    url = build_authorization_url(mode=request.mode, state=state)
    return ConnectionResponse(authorization_url=url, state=state, mode=request.mode)


@router.get("/oauth/callback")
async def oauth_callback(
    code: str | None = None,
    state: str | None = None,
) -> JSONResponse:
    if not state:
        return JSONResponse(status_code=400, content={"code": "OAUTH_STATE_MISMATCH"})
    workspace_id = _state_store.consume(state)
    if workspace_id is None:
        return JSONResponse(status_code=400, content={"code": "OAUTH_STATE_MISMATCH"})
    # Real token exchange arrives with the provider adapter; the vault is wired.
    return JSONResponse(status_code=200, content={"status": "CONNECTED"})


__all__ = ["router"]
