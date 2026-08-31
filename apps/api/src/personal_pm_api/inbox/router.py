"""Source artifact upload endpoints."""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from personal_pm_api.identity.router import current_actor
from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.inbox.models import SourceArtifactModel
from personal_pm_api.inbox.repository import SourceArtifactRepository
from personal_pm_api.inbox.schemas import (
    UploadInitiationRequest,
    UploadInitiationResponse,
    validate_source_filename,
    validate_source_upload,
)
from personal_pm_api.security.uploads import MAX_UPLOAD_BYTES, scan_upload
from personal_pm_api.shared.db import database_session

router = APIRouter(prefix="/api/v1", tags=["source-artifacts"])


async def _session_dep() -> AsyncIterator[AsyncSession]:
    async with database_session() as session:
        yield session


async def _persist_artifact(
    *,
    filename: str,
    content_type: str,
    size_bytes: int,
    sha256: str | None,
    actor: CurrentActor,
    session: AsyncSession,
) -> UploadInitiationResponse:
    validate_source_filename(filename)
    artifact_id = uuid4()
    storage_key = f"workspaces/{actor.workspace_id}/source-artifacts/{artifact_id}/{filename}"
    artifact = await SourceArtifactRepository(session).add(
        SourceArtifactModel(
            id=artifact_id,
            workspace_id=actor.workspace_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256=sha256,
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


async def _read_bounded_upload(request: Request) -> bytes | None:
    content_length = request.headers.get("Content-Length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
            if declared_size < 0 or declared_size > MAX_UPLOAD_BYTES:
                return None
        except ValueError:
            return None
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/inbox/sources", response_model=UploadInitiationResponse, status_code=201)
async def upload_source(
    request: Request,
    filename: Annotated[str, Query(min_length=1, max_length=255)],
    actor: Annotated[CurrentActor, Depends(current_actor)],
    session: Annotated[AsyncSession, Depends(_session_dep)],
) -> UploadInitiationResponse | Response:
    validate_source_filename(filename)
    content = await _read_bounded_upload(request)
    if content is None:
        return JSONResponse(
            status_code=422,
            content={"code": "UPLOAD_REJECTED", "detail": "upload exceeds size limit"},
        )
    content_type = request.headers.get("Content-Type", "").partition(";")[0].strip().lower()
    verdict = scan_upload(content, declared_type=content_type)
    if not verdict.allowed:
        return JSONResponse(
            status_code=verdict.status_code,
            content={"code": verdict.code, "detail": verdict.reason},
        )
    return await _persist_artifact(
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        actor=actor,
        session=session,
    )


@router.post(
    "/source-artifacts/uploads",
    response_model=UploadInitiationResponse,
    status_code=201,
    deprecated=True,
)
async def initiate_upload(
    request: UploadInitiationRequest,
    _actor: Annotated[CurrentActor, Depends(current_actor)],
) -> Response:
    validate_source_upload(request.content_type, request.size_bytes)
    validate_source_filename(request.filename)
    return JSONResponse(
        status_code=410,
        content={
            "code": "UPLOAD_FLOW_REPLACED",
            "detail": "send file bytes to /api/v1/inbox/sources",
        },
    )
