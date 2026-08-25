"""Source artifact upload endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.identity.router import current_actor
from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.inbox.models import SourceArtifactModel
from personal_pm_api.inbox.repository import SourceArtifactRepository
from personal_pm_api.inbox.schemas import (
    UploadInitiationRequest,
    UploadInitiationResponse,
    validate_source_upload,
)
from personal_pm_api.shared.db import database_session

router = APIRouter(prefix="/api/v1", tags=["source-artifacts"])


async def _session_dep() -> AsyncIterator[AsyncSession]:
    async with database_session() as session:
        yield session


@router.post(
    "/source-artifacts/uploads",
    response_model=UploadInitiationResponse,
    status_code=201,
)
async def initiate_upload(
    request: UploadInitiationRequest,
    actor: Annotated[CurrentActor, Depends(current_actor)],
    session: Annotated[AsyncSession, Depends(_session_dep)],
) -> UploadInitiationResponse:
    validate_source_upload(request.content_type, request.size_bytes)

    artifact_id = uuid4()
    storage_key = (
        f"workspaces/{actor.workspace_id}/source-artifacts/{artifact_id}/{request.filename}"
    )
    artifact = await SourceArtifactRepository(session).add(
        SourceArtifactModel(
            id=artifact_id,
            workspace_id=actor.workspace_id,
            filename=request.filename,
            content_type=request.content_type,
            size_bytes=request.size_bytes,
            sha256=request.sha256,
            storage_key=storage_key,
            status="NEW",
        )
    )
    await session.commit()
    return UploadInitiationResponse(
        id=str(artifact.id),
        storage_key=artifact.storage_key,
        status=artifact.status,
    )
