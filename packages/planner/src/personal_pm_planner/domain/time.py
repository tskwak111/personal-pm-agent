"""UTC-aware time primitives.

The Planner never reads wall-clock time; instants enter as explicit inputs and
are normalized to UTC while the caller preserves the original expression.
"""

from datetime import UTC, datetime


def require_aware_utc(value: datetime) -> datetime:
    """Validate that *value* is timezone-aware and return it normalized to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)
