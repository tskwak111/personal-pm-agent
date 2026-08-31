"""Privacy-safe UX telemetry intake."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from enum import StrEnum
from importlib.metadata import version
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field

from personal_pm_api.identity.router import current_actor
from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.telemetry.emitter import TelemetryEmitter
from personal_pm_api.telemetry.logging import hash_workspace_id


class UxEventName(StrEnum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    CANDIDATE_CONFIRMED = "candidate_confirmed"
    PROPOSAL_APPROVED = "proposal_approved"
    AGENT_OPENED = "agent_opened"
    BRIEFING_VIEWED = "briefing_viewed"


UX_EVENT_NAMES = tuple(UxEventName)

LOGGER = logging.getLogger("personal_pm_api.analytics")
router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class UxEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    name: UxEventName
    duration_ms: int = Field(ge=0, le=3_600_000)


class UxEventAccepted(BaseModel):
    accepted: bool


@router.post(
    "/ux-events",
    response_model=UxEventAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def record_ux_event(
    body: UxEventRequest,
    request: Request,
    actor: Annotated[CurrentActor, Depends(current_actor)],
) -> UxEventAccepted:
    event = TelemetryEmitter(code_version=version("personal-pm-api")).ux_event(
        trace_id=str(request.state.correlation_id),
        workspace_hash=hash_workspace_id(str(actor.workspace_id)),
        name=body.name,
        duration_ms=body.duration_ms,
    )
    LOGGER.info(json.dumps(asdict(event), sort_keys=True, separators=(",", ":")))
    return UxEventAccepted(accepted=True)


__all__ = ["UX_EVENT_NAMES", "router"]
