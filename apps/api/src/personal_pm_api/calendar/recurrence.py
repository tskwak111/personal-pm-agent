"""Deterministic recurrence expansion (weekly RRULE subset)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class RecurrenceInstance:
    start_at: datetime
    end_at: datetime
    sequence: int


def expand_weekly(
    first_start: datetime,
    *,
    duration_minutes: int,
    count: int,
) -> tuple[RecurrenceInstance, ...]:
    """Expand a weekly recurrence into exactly *count* deterministic instances."""
    if count <= 0:
        return ()
    duration = timedelta(minutes=duration_minutes)
    week = timedelta(weeks=1)
    return tuple(
        RecurrenceInstance(
            start_at=first_start + week * index,
            end_at=first_start + week * index + duration,
            sequence=index,
        )
        for index in range(count)
    )


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


__all__ = ["RecurrenceInstance", "expand_weekly", "ensure_utc"]
