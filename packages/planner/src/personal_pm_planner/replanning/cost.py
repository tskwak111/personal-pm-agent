"""Change-cost table and lexicographic replanning metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

FREEZE_WINDOW_MINUTES = 120

MOVE_COSTS = {
    "frozen_window": 1000,
    "to_other_day": 40,
    "removed_from_today": 25,
    "same_day_over_two_hours": 10,
    "adjacent_swap": 2,
    "add_flexible": 1,
}

LEXICOGRAPHIC_FIELDS = (
    "hard_constraint_violations",
    "authorization_violations",
    "critical_milestones",
    "base_unallocated_minutes",
    "high_milestones",
    "safety_unallocated_minutes",
    "change_cost",
    "context_switches",
    "energy_mismatch",
)


@dataclass(frozen=True, slots=True)
class ReplanMetrics:
    hard_constraint_violations: int
    authorization_violations: int
    critical_milestones: int
    base_unallocated_minutes: int
    high_milestones: int
    safety_unallocated_minutes: int
    change_cost: int
    context_switches: int
    energy_mismatch: int


def metrics_tuple(metrics: ReplanMetrics) -> tuple[int, ...]:
    return tuple(getattr(metrics, field_name) for field_name in LEXICOGRAPHIC_FIELDS)


def is_in_freeze_window(start_at: datetime, now_utc: datetime) -> bool:
    """Anything starting before ``now + freeze`` may not be auto-moved."""
    return start_at <= now_utc + timedelta(minutes=FREEZE_WINDOW_MINUTES)


def move_cost(old_start: datetime, new_start: datetime) -> int:
    if old_start.date() != new_start.date():
        return MOVE_COSTS["to_other_day"]
    delta_minutes = abs((new_start - old_start).total_seconds() // 60)
    if delta_minutes >= 120:
        return MOVE_COSTS["same_day_over_two_hours"]
    if delta_minutes == 0:
        return 0
    return MOVE_COSTS["adjacent_swap"]
