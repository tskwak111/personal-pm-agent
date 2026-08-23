"""Optimistic concurrency helpers."""

from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.planning.models import TaskModel
from personal_pm_api.shared.errors import StaleObjectVersionError


async def update_with_version(
    session: AsyncSession,
    model: type[TaskModel],
    object_id: str,
    expected_version: int,
    values: dict[str, object],
    *,
    workspace_id: str | None = None,
) -> TaskModel:
    """Update only when the stored version matches; bump version atomically."""
    from uuid import UUID

    criteria = [model.id == UUID(object_id), model.version == expected_version]
    if workspace_id is not None:
        criteria.append(model.workspace_id == UUID(workspace_id))
    statement = (
        update(model).where(*criteria).values(**values, version=model.version + 1).returning(model)
    )
    result = await session.execute(statement)
    updated = result.scalar_one_or_none()
    if updated is None:
        raise StaleObjectVersionError(object_id, expected_version)
    return updated
