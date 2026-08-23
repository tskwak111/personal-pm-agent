"""Idempotent command envelopes.

A client-supplied key may execute exactly once; replays raise a typed error
instead of duplicating side effects.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_pm_api.shared.orm import Base, created_at


class IdempotencyKeyAlreadyUsed(Exception):
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"idempotency key already used: {key}")


class IdempotencyRecordModel(Base):
    __tablename__ = "idempotency_records"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    response_json: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at()


class ReservedKey:
    __slots__ = ("key",)

    def __init__(self, key: str) -> None:
        self.key = key


async def reserve_key(
    session: AsyncSession,
    key: str,
    workspace_id: UUID | str,
    *,
    request_fingerprint: str | None = None,
) -> bool:
    """Insert the key row; return False when it was already reserved.

    The conflicting insert is rolled back to a SAVEPOINT so the caller's
    transaction stays usable.
    """
    record = IdempotencyRecordModel(
        key=key,
        workspace_id=workspace_id if isinstance(workspace_id, UUID) else UUID(workspace_id),
        request_fingerprint=request_fingerprint or uuid4().hex,
    )
    session.add(record)
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError:
        return False
    return True


async def find_replay(session: AsyncSession, key: str) -> dict[str, object] | None:
    statement = select(IdempotencyRecordModel).where(IdempotencyRecordModel.key == key)
    record = (await session.execute(statement)).scalar_one_or_none()
    return record.response_json if record else None


__all__ = [
    "IdempotencyKeyAlreadyUsed",
    "IdempotencyRecordModel",
    "ReservedKey",
    "reserve_key",
]
