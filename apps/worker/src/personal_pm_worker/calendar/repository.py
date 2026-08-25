"""In-memory outbox repository for executor tests (deterministic fakes)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


class PermanentFailureError(Exception):
    """A non-retryable provider rejection."""


@dataclass
class _Record:
    id: str
    idempotency_key: str
    command: dict[str, object]
    execution_status: str = "PENDING"
    external_event_id: str | None = None


@dataclass
class InMemoryOutboxRepository:
    records: dict[str, _Record] = field(default_factory=dict)

    async def add_pending(self, *, idempotency_key: str, command: dict[str, object]) -> str:
        record_id = uuid.uuid4().hex
        self.records[record_id] = _Record(
            id=record_id, idempotency_key=idempotency_key, command=command
        )
        return record_id

    def get(self, record_id: str) -> _Record:
        record = self.records.get(record_id)
        if record is None:
            raise KeyError(record_id)
        return record

    async def find_success_by_idempotency(self, idempotency_key: str) -> _Record | None:
        for record in self.records.values():
            if record.idempotency_key == idempotency_key and record.execution_status == "SUCCEEDED":
                return record
        return None

    async def link_existing_result(self, record_id: str, existing: Any) -> None:
        record = self.get(record_id)
        record.execution_status = "SUCCEEDED"
        record.external_event_id = existing.external_event_id

    async def mark_succeeded(self, record_id: str, external_event_id: str) -> None:
        record = self.get(record_id)
        record.execution_status = "SUCCEEDED"
        record.external_event_id = external_event_id

    async def mark_failed(self, record_id: str, error: str) -> None:
        record = self.get(record_id)
        record.execution_status = "FAILED"
        record.last_error = error  # type: ignore[attr-defined]

    async def execution_status(self, record_id: str) -> str:
        return self.get(record_id).execution_status

    async def external_event_id(self, record_id: str) -> str | None:
        return self.get(record_id).external_event_id


__all__ = ["InMemoryOutboxRepository", "PermanentFailureError"]
