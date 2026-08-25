"""Sync operation store with idempotent webhook acceptance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SyncOperation:
    operation_id: str
    connection_id: str
    message_number: int


@dataclass
class InMemorySyncOperationStore:
    by_key: dict[str, SyncOperation] = field(default_factory=dict)

    async def get_or_create(self, operation_key: str, payload: dict[str, Any]) -> SyncOperation:
        existing = self.by_key.get(operation_key)
        if existing is not None:
            return existing
        operation = SyncOperation(
            operation_id=operation_key,
            connection_id=str(payload["connection_id"]),
            message_number=int(payload.get("message_number", 0)),
        )
        self.by_key[operation_key] = operation
        return operation


__all__ = ["InMemorySyncOperationStore", "SyncOperation"]
