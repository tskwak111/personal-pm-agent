"""Daily plannable capacity factors and slot rounding."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

CAPACITY_FACTORS = {
    "normal": 0.80,
    "low": 0.65,
    "crunch": 0.85,
}


def floor_to_slot(minutes: float, slot_minutes: int) -> int:
    """Floor to slot boundary with a deterministic float-noise guard.

    ``raw * factor`` can land epsilon below an exact multiple (e.g.
    ``375 * 0.8 -> 299.999...``); rounding first keeps results stable
    across platforms, which the determinism gate requires.
    """
    return int(math.floor(round(minutes / slot_minutes, 6)) * slot_minutes)


def local_day(instant: datetime, user_timezone: str) -> date:
    return instant.astimezone(ZoneInfo(user_timezone)).date()


def day_bounds(day: date, user_timezone: str) -> tuple[datetime, datetime]:
    """UTC instants for local midnight and the next local midnight."""
    tz = ZoneInfo(user_timezone)
    start_local = datetime.combine(day, time(0, 0), tzinfo=tz)
    from datetime import timedelta

    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)
