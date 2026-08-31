"""Version-bound proposal decision endpoint."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from personal_pm_api.approvals.service import ApprovalService
from personal_pm_api.identity.router import current_actor
from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.shared.db import session_factory
from personal_pm_api.shared.errors import NotFoundError

router = APIRouter(prefix="/api/v1", tags=["proposals"])


class ApproveProposalRequest(BaseModel):
    decision: Literal["approve", "reject"]
    expected_version: int = Field(ge=1, strict=True)


class ProposalApproveResponse(BaseModel):
    id: str
    status: str
    approval_level: str
    reason: str | None = None


def _approval_service() -> ApprovalService:
    return ApprovalService(session_factory())


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalApproveResponse)
async def approve_proposal(
    proposal_id: UUID,
    request: ApproveProposalRequest,
    response: Response,
    actor: Annotated[CurrentActor, Depends(current_actor)],
    service: Annotated[ApprovalService, Depends(_approval_service)],
) -> ProposalApproveResponse:
    if request.decision == "approve":
        outcome = await service.approve(
            actor,
            proposal_id=str(proposal_id),
            expected_version=request.expected_version,
        )
    else:
        outcome = await service.reject(
            actor,
            proposal_id=str(proposal_id),
            expected_version=request.expected_version,
        )

    if outcome.status == "NOT_FOUND":
        raise NotFoundError()
    if outcome.status in {"CONFLICT", "SUPERSEDED"}:
        response.status_code = 409
    elif outcome.status == "INVALID":
        response.status_code = 422
    return ProposalApproveResponse(
        id=str(proposal_id),
        status=outcome.status,
        approval_level=outcome.approval_level,
        reason=outcome.reason,
    )
