"""Effective deadline interpretation.

Date-only deadlines keep their fact untouched; the conservative calculation
boundary is local midnight of that date, never an invented 23:59.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from personal_pm_planner.domain.work import MilestoneSnapshot


@dataclass(frozen=True, slots=True)
class EffectiveDeadline:
    instant: datetime | None
    assumption: str


def effective_deadline(milestone: MilestoneSnapshot, user_timezone: str) -> EffectiveDeadline:
    if milestone.deadline_time_known and milestone.deadline_at is not None:
        return EffectiveDeadline(
            instant=milestone.deadline_at.astimezone(UTC),
            assumption="VERIFIED_INSTANT",
        )
    if milestone.deadline_date_known and milestone.deadline_date is not None:
        local_midnight = datetime.combine(
            milestone.deadline_date,
            time(0, 0),
            tzinfo=ZoneInfo(user_timezone),
        )
        return EffectiveDeadline(
            instant=local_midnight.astimezone(UTC),
            assumption="DATE_ONLY_START_OF_DAY",
        )
    return EffectiveDeadline(instant=None, assumption="NO_DEADLINE")
