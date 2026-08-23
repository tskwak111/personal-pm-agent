"""Task read endpoint with strict workspace ownership."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
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


class TaskPatchRequest(BaseModel):
    expected_version: int
    title: str | None = None


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    request: TaskPatchRequest,
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> TaskResponse:
    """Workspace-scoped update guarded by the expected object version."""
    from datetime import UTC, datetime
    from uuid import UUID

    from sqlalchemy import select

    from personal_pm_api.audit.repository import AuditRepository
    from personal_pm_api.planning.models import TaskModel
    from personal_pm_api.shared.concurrency import update_with_version
    from personal_pm_api.shared.errors import StaleObjectVersionError

    values: dict[str, object] = {}
    if request.title is not None:
        values["title"] = request.title

    async with database_session() as session:
        statement = select(TaskModel).where(
            TaskModel.id == UUID(task_id),
            TaskModel.workspace_id == actor.workspace_id,
        )
        existing = (await session.execute(statement)).scalar_one_or_none()
        if existing is None:
            raise NotFoundError()

        try:
            updated: TaskModel = await update_with_version(
                session,
                TaskModel,
                task_id,
                request.expected_version,
                values,
                workspace_id=str(actor.workspace_id),
            )
        except StaleObjectVersionError:
            await session.rollback()
            raise

        audits = AuditRepository(session)
        await audits.append(
            workspace_id=actor.workspace_id,
            actor_user_id=actor.user_id,
            entity_kind="task",
            entity_id=task_id,
            reason="task.update:" + ",".join(sorted(values)),
            rule_basis=("REQ-CORE-014",),
            trace_id=f"sess:{actor.session_id}",
            reversible=True,
            occurred_at=datetime.now(UTC),
            before_state={"title": existing.title},
            after_state=dict(values),
        )
        await session.commit()

    return TaskResponse(
        id=str(updated.id),
        title=updated.title,
        status=updated.status,
        version=updated.version,
    )


class TaskTransitionBody(BaseModel):
    expected_version: int
    target_status: str
    completion_confirmed: bool = False
    waiting_resolved: bool = False
    blocker_resolved: bool = False
    waiting_reason: str | None = None


@router.post("/tasks/{task_id}/transition", response_model=TaskResponse)
async def transition_task(
    task_id: str,
    request: TaskTransitionBody,
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> TaskResponse:
    from personal_pm_api.workspaces.schemas import TaskTransitionRequest
    from personal_pm_api.workspaces.service import WorkspaceService

    service_request = TaskTransitionRequest(
        expected_version=request.expected_version,
        target_status=request.target_status,
        completion_confirmed=request.completion_confirmed,
        waiting_resolved=request.waiting_resolved,
        blocker_resolved=request.blocker_resolved,
        waiting_reason=request.waiting_reason,
    )
    async with database_session() as session:
        updated = await WorkspaceService(session).transition_task(
            actor_user_id=actor.user_id,
            workspace_id=actor.workspace_id,
            session_id=actor.session_id,
            task_id=task_id,
            request=service_request,
        )
    return TaskResponse(
        id=str(updated.id),
        title=updated.title,
        status=updated.status,
        version=updated.version,
    )


class MilestonePatchBody(BaseModel):
    expected_version: int
    deadline_date: str | None = None


class ProposalSummary(BaseModel):
    id: str
    authorization_level: str
    status: str


class MilestoneChangeResponse(BaseModel):
    applied: bool
    proposal: ProposalSummary | None


@router.patch("/milestones/{milestone_id}")
async def patch_milestone(
    milestone_id: str,
    request: MilestonePatchBody,
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> Response:
    import datetime as dt

    from personal_pm_api.workspaces.service import WorkspaceService

    deadline_date = dt.date.fromisoformat(request.deadline_date) if request.deadline_date else None
    async with database_session() as session:
        applied, proposal = await WorkspaceService(session).request_milestone_deadline_change(
            actor_user_id=actor.user_id,
            workspace_id=actor.workspace_id,
            session_id=actor.session_id,
            milestone_id=milestone_id,
            expected_version=request.expected_version,
            deadline_date=deadline_date,
        )
    if proposal is not None:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=202,
            content={
                "applied": False,
                "proposal": {
                    "id": str(proposal.id),
                    "authorization_level": proposal.approval_level,
                    "status": proposal.status,
                },
            },
        )
    assert applied is not None
    return JSONResponse(status_code=200, content={"applied": True, "proposal": None})
