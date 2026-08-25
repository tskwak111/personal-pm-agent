"""Webhook-triggered delta sync plus periodic recovery polling.

A lost webhook is not a lost sync: every registered pending change is
reconciled by the 15-minute recovery window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from personal_pm_worker.calendar.sync_jobs import InMemorySyncOperationStore

SYNC_RECOVERY_INTERVAL_SECONDS = 15 * 60


@dataclass
class SyncScheduler:
    operations: InMemorySyncOperationStore = field(default_factory=InMemorySyncOperationStore)
    clock: Any = None
    sync_target: Any = None
    _pending_changes: list[dict[str, str]] = field(default_factory=list)
    _last_recovery_at: float = 0.0

    async def accept_webhook(self, payload: dict[str, Any]) -> Any:
        """Idempotently accept a webhook; duplicate deliveries deduplicate."""
        operation_key = (
            f"calendar-sync:{payload['channel_id']}:"
            f"{payload['resource_state']}:{payload['message_number']}"
        )
        operation = await self.operations.get_or_create(operation_key, payload)
        external_id = payload.get("external_event_id")
        if external_id:
            await self.sync_target.run_delta_sync(str(external_id))
        return operation

    async def register_pending_change(self, external_event_id: str, *, connection_id: str) -> None:
        self._pending_changes.append(
            {"external_event_id": external_event_id, "connection_id": connection_id}
        )

    def _recovery_due(self) -> bool:
        now = float(self.clock.now)
        return (now - self._last_recovery_at) >= SYNC_RECOVERY_INTERVAL_SECONDS or (
            self._last_recovery_at == 0.0 and now >= SYNC_RECOVERY_INTERVAL_SECONDS
        )

    async def run_due(self) -> int:
        """Recover any pending changes missed by webhooks."""
        if not self._recovery_due():
            return 0
        recovered = 0
        for change in self._pending_changes:
            await self.sync_target.run_delta_sync(change["external_event_id"])
            recovered += 1
        self._pending_changes.clear()
        if recovered:
            self._last_recovery_at = float(self.clock.now)
        return recovered


__all__ = ["SYNC_RECOVERY_INTERVAL_SECONDS", "SyncScheduler"]
