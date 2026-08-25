"""Proposal approval endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from personal_pm_api.identity.router import current_actor
from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.shared.db import database_session
from personal_pm_api.shared.errors import NotFoundError

router = APIRouter(prefix="/api/v1", tags=["proposals"])


class ApproveProposalRequest(BaseModel):
    decision: str = "approve"


class ProposalApproveResponse(BaseModel):
    id: str
    status: str
    approval_level: str


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalApproveResponse)
async def approve_proposal(
    proposal_id: str,
    request: ApproveProposalRequest,
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> ProposalApproveResponse:
    from uuid import UUID

    from personal_pm_api.approvals.models import ProposalModel

    async with database_session() as session:
        stmt = select(ProposalModel).where(
            ProposalModel.id == UUID(proposal_id),
            ProposalModel.workspace_id == actor.workspace_id,
        )
        model = (await session.execute(stmt)).scalar_one_or_none()
        if model is None:
            raise NotFoundError()
        # Minimal state change: mark as approved if pending
        if model.status == "pending" and request.decision == "approve":
            model.status = "approved"
            await session.commit()
            await session.refresh(model)
        return ProposalApproveResponse(
            id=str(model.id), status=model.status, approval_level=model.approval_level
        )
