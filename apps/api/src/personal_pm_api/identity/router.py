"""Identity endpoints and the current-actor dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator
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
    seed_demo: bool = False


class SessionResponse(BaseModel):
    token: str
    user_id: str


class TestResetResponse(BaseModel):
    seeded: bool


@router.post("/identity/test-session", response_model=SessionResponse)
async def create_test_session(request: TestSessionRequest) -> SessionResponse:
    from personal_pm_api.settings import ApiSettings

    if ApiSettings().environment not in ("local", "test"):
        raise HTTPException(status_code=404)
    async with database_session() as session:
        issued = await IdentityService(session).test_provider_session(email=request.email)
        if issued is not None and request.seed_demo:
            from personal_pm_api.identity.test_fixture import reset_and_seed_browser_fixture

            await reset_and_seed_browser_fixture(session, issued.user_id)
        await session.commit()
    assert issued is not None
    return SessionResponse(token=issued.raw_token, user_id=str(issued.user_id))


@router.post("/identity/test-reset", response_model=TestResetResponse)
async def reset_test_fixture(
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> TestResetResponse:
    from personal_pm_api.settings import ApiSettings

    if ApiSettings().environment not in ("local", "test"):
        raise HTTPException(status_code=404)
    from personal_pm_api.identity.test_fixture import reset_and_seed_browser_fixture

    async with database_session() as session:
        await reset_and_seed_browser_fixture(session, actor.user_id)
        await session.commit()
    return TestResetResponse(seeded=True)
