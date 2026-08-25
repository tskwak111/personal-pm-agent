"""Import provider events into external snapshots with availability typing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

AVAILABILITY_TYPES = {
    "FIXED_BUSY": True,
    "TENTATIVE": False,
    "ALL_DAY_INFORMATION": False,
    "MOVABLE_COMMITMENT": True,
}


def classify_event(event: Any) -> str:
    """Deterministic mapping from a provider event to availability type."""
    if event.managed_focus_block:
        return "MOVABLE_COMMITMENT"
    if event.all_day and not event.blocks_time:
        return "ALL_DAY_INFORMATION"
    if event.status == "tentative":
        return "TENTATIVE"
    return "FIXED_BUSY"


class CalendarSyncService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def import_event(self, workspace_id: str | UUID, event: Any) -> Any:
        from personal_pm_api.calendar.models import ExternalCalendarEventModel

        async with self._factory() as session:
            statement = select(ExternalCalendarEventModel).where(
                ExternalCalendarEventModel.workspace_id == UUID(str(workspace_id)),
                ExternalCalendarEventModel.external_event_id == event.external_id,
            )
            existing = (await session.execute(statement)).scalar_one_or_none()

            availability = classify_event(event)
            if existing is None:
                model = ExternalCalendarEventModel(
                    id=uuid4(),
                    workspace_id=UUID(str(workspace_id)),
                    external_event_id=event.external_id,
                    title=event.title,
                    start_at=event.start_at,
                    end_at=event.end_at,
                    all_day=bool(event.all_day),
                    blocks_capacity=AVAILABILITY_TYPES[availability],
                    availability_type=availability,
                    provider_status=str(getattr(event, "status", "confirmed")),
                    managed_focus_block=bool(event.managed_focus_block),
                    sync_status="SYNCED",
                    provider_version=getattr(event, "provider_version", None),
                )
                session.add(model)
                await session.commit()
                return ImportedEvent.from_model(model)

            existing.title = event.title
            existing.start_at = event.start_at
            existing.end_at = event.end_at
            existing.all_day = bool(event.all_day)
            existing.availability_type = availability
            existing.blocks_capacity = AVAILABILITY_TYPES[availability]
            existing.provider_status = str(getattr(event, "status", "confirmed"))
            existing.updated_at = datetime.now(UTC)
            await session.commit()
            return ImportedEvent.from_model(existing)

    async def apply_provider_update(self, workspace_id: str | UUID, event: Any) -> Any:
        """External edit to a managed focus block: record it, never force back.

        Field ownership: start/end moves by the provider are surfaced as a
        pending internal reconciliation instead of an outbound restore.
        """
        from personal_pm_api.calendar.models import ExternalCalendarEventModel

        async with self._factory() as session:
            statement = select(ExternalCalendarEventModel).where(
                ExternalCalendarEventModel.workspace_id == UUID(str(workspace_id)),
                ExternalCalendarEventModel.external_event_id == event.external_id,
            )
            model = (await session.execute(statement)).scalar_one_or_none()
            if model is None:
                from personal_pm_api.shared.errors import NotFoundError

                raise NotFoundError()

            moved = model.start_at != event.start_at or model.end_at != event.end_at
            model.title = event.title  # PROVIDER-owned field
            if moved:
                model.start_at = event.start_at
                model.end_at = event.end_at
                model.pending_internal_reconciliation = True
                model.outbound_restore_requested = False
            if event.managed_focus_block and not model.managed_focus_block:
                model.managed_focus_block = True
            model.updated_at = datetime.now(UTC)
            await session.commit()
            return ImportedEvent.from_model(model)

    async def active_events(self, workspace_id: str | UUID) -> list[Any]:
        from personal_pm_api.calendar.models import ExternalCalendarEventModel

        async with self._factory() as session:
            statement = select(ExternalCalendarEventModel).where(
                ExternalCalendarEventModel.workspace_id == UUID(str(workspace_id)),
                ExternalCalendarEventModel.sync_status != "EXTERNALLY_DELETED",
            )
            rows = (await session.execute(statement)).scalars().all()
            return [ImportedEvent.from_model(row) for row in rows]

    async def apply_provider_deletion(self, external_event_id: str) -> Any:
        from personal_pm_api.calendar.models import ExternalCalendarEventModel

        async with self._factory() as session:
            statement = select(ExternalCalendarEventModel).where(
                ExternalCalendarEventModel.external_event_id == external_event_id
            )
            model = (await session.execute(statement)).scalar_one_or_none()
            if model is None:
                from personal_pm_api.shared.errors import NotFoundError

                raise NotFoundError()
            # Tombstone: never hard-delete managed history.
            model.sync_status = "EXTERNALLY_DELETED"
            model.deleted_at = datetime.now(UTC)
            await session.commit()
            return ImportedEvent.from_model(model)


class ImportedEvent:
    def __init__(self, model: Any) -> None:
        self.id = str(model.id)
        self.external_event_id = model.external_event_id
        self.title = model.title
        self.availability_type = model.availability_type
        self.blocks_capacity = model.blocks_capacity
        self.sync_status = model.sync_status
        self.deleted_at = model.deleted_at
        self.pending_internal_reconciliation = model.pending_internal_reconciliation
        self.outbound_restore_requested = model.outbound_restore_requested

    @classmethod
    def from_model(cls, model: Any) -> ImportedEvent:
        return cls(model)
