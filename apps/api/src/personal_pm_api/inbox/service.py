"""Inbox lifecycle application service (New → … → Structured/Failed)."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from personal_pm_api.inbox.models import InboxItemModel, SourceArtifactModel, transition_inbox


class InboxItem:
    """Lightweight read model returned by the service."""

    def __init__(self, model: InboxItemModel) -> None:
        self.id = str(model.id)
        self.workspace_id = str(model.workspace_id)
        self.source_artifact_id = (
            str(model.source_artifact_id) if model.source_artifact_id else None
        )
        self.kind = model.kind
        self.status = model.status
        self.raw_text = model.raw_text
        self.failure_reason = model.failure_reason


class InboxService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def create_from_text(self, actor: Any, text: str) -> InboxItem:
        async with self._factory() as session:
            artifact = SourceArtifactModel(
                id=uuid4(),
                workspace_id=UUID(str(actor.workspace_id)),
                filename="inline.txt",
                content_type="text/plain",
                size_bytes=len(text.encode("utf-8")),
                sha256=None,
                storage_key=(
                    f"workspaces/{actor.workspace_id}/source-artifacts/{uuid4()}/inline.txt"
                ),
                status="READY",
            )
            session.add(artifact)
            await session.flush()

            item = InboxItemModel(
                id=uuid4(),
                workspace_id=UUID(str(actor.workspace_id)),
                source_artifact_id=artifact.id,
                kind="text",
                raw_text=text,
                status="NEW",
            )
            session.add(item)
            await session.commit()
            return InboxItem(item)

    async def get(self, actor: Any, item_id: str) -> InboxItem | None:
        async with self._factory() as session:
            statement = select(InboxItemModel).where(
                InboxItemModel.id == UUID(str(item_id)),
                InboxItemModel.workspace_id == UUID(str(actor.workspace_id)),
            )
            model = (await session.execute(statement)).scalar_one_or_none()
            return InboxItem(model) if model else None

    async def mark(self, item_id: str, target_status: str) -> InboxItem:
        async with self._factory() as session:
            model = await session.get(InboxItemModel, UUID(str(item_id)))
            if model is None:
                from personal_pm_api.shared.errors import NotFoundError

                raise NotFoundError()
            model.status = transition_inbox(model.status, target_status)
            await session.commit()
            return InboxItem(model)

    async def mark_failed(self, item_id: str, reason: str) -> InboxItem:
        async with self._factory() as session:
            model = await session.get(InboxItemModel, UUID(str(item_id)))
            if model is None:
                from personal_pm_api.shared.errors import NotFoundError

                raise NotFoundError()
            model.status = transition_inbox(model.status, "FAILED")
            model.failure_reason = reason
            await session.commit()
            return InboxItem(model)
