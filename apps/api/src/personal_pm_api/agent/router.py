"""Authenticated replay stream for agent operation events."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse

from personal_pm_api.agent.operations import AgentOperationService, StepEventView
from personal_pm_api.identity.router import current_actor
from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.shared.db import session_factory
from personal_pm_api.shared.errors import NotFoundError

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


def _encode_event(event: StepEventView) -> str:
    data = json.dumps(
        {"step": event.step, "status": event.status, "sequence": event.sequence},
        separators=(",", ":"),
    )
    return f"id: {event.sequence}\nevent: operation.step\ndata: {data}\n\n"


@router.get("/operations/{operation_id}/stream")
async def stream_operation(
    operation_id: str,
    actor: Annotated[CurrentActor, Depends(current_actor)],
    last_event_id: Annotated[int | None, Query(ge=-1)] = None,
    last_event_header: Annotated[int | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    service = AgentOperationService(session_factory())
    if await service.get(actor, operation_id) is None:
        raise NotFoundError()
    cursor = last_event_id if last_event_id is not None else last_event_header
    events = [
        event
        for event in await service.events(actor, operation_id)
        if event.sequence > (cursor if cursor is not None else -1)
    ]

    # ponytail: replay-and-close avoids unsafe process-local polling; use broker
    # fanout when multi-process live streaming is required.
    async def replay() -> AsyncIterator[str]:
        if not events:
            yield ": replay complete\n\n"
        for event in events:
            yield _encode_event(event)

    return StreamingResponse(
        replay(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


__all__ = ["router"]
