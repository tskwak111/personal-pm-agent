"""Outbox command executor: claim → execute → verify, idempotently.

No false success: an execution is SUCCEEDED only after the provider result
is verified and an external event id is recorded. Timeouts after a provider
side-effect are reconciled through provider-side idempotency keys.
"""

from __future__ import annotations

from typing import Any


class CalendarCommandExecutor:
    def __init__(self, *, repository: Any, adapter: Any) -> None:
        self.repository = repository
        self.adapter = adapter

    async def execute(self, outbox_id: str) -> str:
        record = self.repository.get(outbox_id)
        existing = await self.repository.find_success_by_idempotency(record.idempotency_key)
        if existing is not None:
            # Duplicate delivery of an already-successful command.
            await self.repository.link_existing_result(record.id, existing)
            return "SUCCEEDED"

        try:
            result = await self.adapter.execute(dict(record.command))
        except TimeoutError:
            # Unknown outcome: leave PENDING so redelivery reconciles; never
            # mark success or failure on an ambiguous timeout.
            return "PENDING"

        verified = await self.adapter.verify(result)
        external_event_id = result.get("external_event_id")
        if not verified or external_event_id is None:
            from personal_pm_worker.calendar.repository import PermanentFailureError

            await self.repository.mark_failed(record.id, "verification failed")
            raise PermanentFailureError("provider result failed verification")

        await self.repository.mark_succeeded(record.id, str(external_event_id))
        return "SUCCEEDED"


__all__ = ["CalendarCommandExecutor"]
