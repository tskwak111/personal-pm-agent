"""Workstream read endpoints (workspace-scoped)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from personal_pm_api.identity.router import current_actor
from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.planning.models import WorkstreamModel
from personal_pm_api.shared.db import database_session

router = APIRouter(prefix="/api/v1", tags=["workstreams"])


class WorkstreamItem(BaseModel):
    id: str
    name: str
    importance: str
    status: str


class WorkstreamListResponse(BaseModel):
    items: list[WorkstreamItem]


@router.get("/workstreams", response_model=WorkstreamListResponse)
async def list_workstreams(
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> WorkstreamListResponse:

    async with database_session() as session:
        statement = (
            select(WorkstreamModel)
            .where(WorkstreamModel.workspace_id == actor.workspace_id)
            .order_by(WorkstreamModel.name)
        )
        rows = (await session.execute(statement)).scalars()
        return WorkstreamListResponse(
            items=[
                WorkstreamItem(
                    id=str(row.id), name=row.name, importance=row.importance, status=row.status
                )
                for row in rows
            ]
        )
