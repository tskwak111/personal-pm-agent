"""In-memory notification service with dedupe by key."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from personal_pm_api.notifications.policy import NotificationIntent


@dataclass
class NotificationRecord:
    id: str
    dedupe_key: str
    title: str
    body: str


@dataclass
class NotificationService:
    _by_key: dict[str, NotificationRecord] = field(default_factory=dict)

    async def enqueue(self, intent: NotificationIntent) -> NotificationRecord:
        """Same dedupe key returns the SAME record (idempotent)."""
        existing = self._by_key.get(intent.dedupe_key)
        if existing is not None:
            return existing
        record = NotificationRecord(
            id=uuid4().hex,
            dedupe_key=intent.dedupe_key,
            title=intent.title,
            body=intent.body,
        )
        self._by_key[intent.dedupe_key] = record
        return record

    async def pending_count(self, dedupe_key: str) -> int:
        return 1 if dedupe_key in self._by_key else 0


__all__ = ["NotificationRecord", "NotificationService"]
