"""Task read endpoint with strict workspace ownership."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from personal_pm_api.identity.router import current_actor
from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.shared.db import database_session
from personal_pm_api.shared.errors import NotFoundError

router = APIRouter(prefix="/api/v1", tags=["tasks"])


class TaskResponse(BaseModel):
    id: str
    title: str
    status: str
    version: int


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str, actor: Annotated[CurrentActor, Depends(current_actor)]
) -> TaskResponse:
    from uuid import UUID

    from sqlalchemy import select

    from personal_pm_api.planning.models import TaskModel

    async with database_session() as session:
        statement = select(TaskModel).where(
            TaskModel.id == UUID(task_id),
            TaskModel.workspace_id == actor.workspace_id,
        )
        model = (await session.execute(statement)).scalar_one_or_none()

    if model is None:
        raise NotFoundError()
    return TaskResponse(
        id=str(model.id), title=model.title, status=model.status, version=model.version
    )
