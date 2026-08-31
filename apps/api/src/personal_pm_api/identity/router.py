"""Identity endpoints and the current-actor dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr

from personal_pm_api.identity.service import IdentityService
from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.shared.db import database_session

router = APIRouter(prefix="/api/v1", tags=["identity"])


async def _identity_service() -> AsyncIterator[IdentityService]:
    async with database_session() as session:
        yield IdentityService(session)


@dataclass(frozen=True, slots=True)
class ActorDependency:
    user_id: str
    workspace_id: str


async def current_actor(
    request: Request,
    service: Annotated[IdentityService, Depends(_identity_service)],
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentActor:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer session")
    raw_token = authorization.removeprefix("Bearer ").strip()
    actor: CurrentActor | None = await service.resolve_actor(raw_token)
    if actor is None or actor.workspace_id is None:
        raise HTTPException(status_code=401, detail="invalid or expired session")
    request.state.workspace_id = str(actor.workspace_id)
    return actor


class TestSessionRequest(BaseModel):
    email: EmailStr


class SessionResponse(BaseModel):
    token: str
    user_id: str


@router.post("/identity/test-session", response_model=SessionResponse)
async def create_test_session(request: TestSessionRequest) -> SessionResponse:
    from personal_pm_api.settings import ApiSettings

    if ApiSettings().environment not in ("local", "test"):
        raise HTTPException(status_code=404)
    async with database_session() as session:
        issued = await IdentityService(session).test_provider_session(email=request.email)
        await session.commit()
    assert issued is not None
    return SessionResponse(token=issued.raw_token, user_id=str(issued.user_id))
