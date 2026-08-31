"""Authenticated browser read-model endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from personal_pm_api.identity.router import current_actor
from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.shared.db import database_session
from personal_pm_api.shared.errors import NotFoundError
from personal_pm_api.views.queries import (
    calendar_view,
    inbox_view,
    project_detail_view,
    projects_view,
    review_view,
    today_view,
)
from personal_pm_api.views.schemas import (
    CalendarResponse,
    InboxResponse,
    ProjectDetailResponse,
    ProjectsResponse,
    ReviewResponse,
    TodayResponse,
)

router = APIRouter(prefix="/api/v1", tags=["views"])


@router.get("/today", response_model=TodayResponse)
async def get_today(
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> TodayResponse:
    async with database_session() as session:
        return await today_view(session, actor)


@router.get("/inbox", response_model=InboxResponse)
async def get_inbox(
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> InboxResponse:
    async with database_session() as session:
        return await inbox_view(session, actor)


@router.get("/projects", response_model=ProjectsResponse)
async def get_projects(
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> ProjectsResponse:
    async with database_session() as session:
        return await projects_view(session, actor)


@router.get("/projects/{workstream_id}", response_model=ProjectDetailResponse)
async def get_project_detail(
    workstream_id: str,
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> ProjectDetailResponse:
    async with database_session() as session:
        detail = await project_detail_view(session, actor, workstream_id)
    if detail is None:
        raise NotFoundError()
    return detail


@router.get("/calendar", response_model=CalendarResponse)
async def get_calendar(
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> CalendarResponse:
    async with database_session() as session:
        return await calendar_view(session, actor)


@router.get("/review", response_model=ReviewResponse)
async def get_review(
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> ReviewResponse:
    async with database_session() as session:
        return await review_view(session, actor)


__all__ = ["router"]
