"""Build unique availability slots with exactly one ownership state each.

Generation order follows Planner Spec section 7: windows are split into slots,
fixed busy events and protected focus blocks reserve their slots first, then
the daily capacity factor converts leftover free minutes into FREE capacity
and BUFFER reserve. Within one pass, every slot carries exactly one state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Protocol, cast

from personal_pm_planner.availability.capacity import floor_to_slot, local_day


class SlotState(StrEnum):
    FREE = "FREE"
    FIXED_EVENT = "FIXED_EVENT"
    PROTECTED_FOCUS_BLOCK = "PROTECTED_FOCUS_BLOCK"
    BUFFER = "BUFFER"


class IntervalLike(Protocol):
    @property
    def start_at(self) -> datetime: ...

    @property
    def end_at(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class Interval:
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True, slots=True)
class Slot:
    id: str
    start_at: datetime
    end_at: datetime
    state: SlotState

    @property
    def minutes(self) -> int:
        return int((self.end_at - self.start_at).total_seconds() // 60)

    @property
    def is_free(self) -> bool:
        return self.state is SlotState.FREE

    def overlaps_interval(self, interval: IntervalLike) -> bool:
        return self.start_at < interval.end_at and interval.start_at < self.end_at


@dataclass(frozen=True, slots=True)
class AvailabilityContext:
    availability_windows: tuple[IntervalLike, ...]
    calendar_events: tuple[object, ...] = ()
    protected_focus_blocks: tuple[Interval, ...] = ()
    slot_minutes: int = 15
    capacity_factor: float = 0.80
    user_timezone: str = "UTC"

    @property
    def fixed_event_intervals(self) -> tuple[Interval, ...]:
        intervals: list[Interval] = []
        for event in self.calendar_events:
            kind = getattr(event, "event_kind", None)
            if kind is not None and getattr(kind, "value", None) == "fixed_busy":
                bounded = cast(IntervalLike, event)
                intervals.append(Interval(start_at=bounded.start_at, end_at=bounded.end_at))
        return tuple(intervals)


def _split_window(
    window: IntervalLike,
    slot_minutes: int,
    counter: list[int],
) -> list[Slot]:
    slots: list[Slot] = []
    step = timedelta(minutes=slot_minutes)
    cursor = window.start_at
    end = window.end_at
    while cursor < end:
        step_end = min(cursor + step, end)
        counter[0] += 1
        slots.append(
            Slot(
                id=f"slot-{cursor.strftime('%Y%m%dT%H%M%S')}-{counter[0]:04d}",
                start_at=cursor,
                end_at=step_end,
                state=SlotState.FREE,
            )
        )
        cursor = step_end
    return slots


def _reserve_intervals(
    slots: list[Slot],
    intervals: tuple[Interval, ...],
    state: SlotState,
) -> list[Slot]:
    if not intervals:
        return slots
    reserved: list[Slot] = []
    for slot in slots:
        hit = any(slot.overlaps_interval(interval) for interval in intervals)
        if hit and slot.state is SlotState.FREE:
            reserved.append(
                Slot(id=slot.id, start_at=slot.start_at, end_at=slot.end_at, state=state)
            )
        else:
            reserved.append(slot)
    return reserved


def _apply_daily_capacity(
    slots: list[Slot],
    capacity_factor: float,
    slot_minutes: int,
    user_timezone: str,
) -> list[Slot]:
    """Convert tail FREE slots of every local day into BUFFER reserve."""
    by_day: dict[date, list[int]] = {}
    for index, slot in enumerate(slots):
        by_day.setdefault(local_day(slot.start_at, user_timezone), []).append(index)

    result = list(slots)
    for day in sorted(by_day):
        free_indexes = [index for index in by_day[day] if result[index].state is SlotState.FREE]
        raw_free_minutes = sum(result[index].minutes for index in free_indexes)
        planned_capacity = floor_to_slot(raw_free_minutes * capacity_factor, slot_minutes)
        allowed_free_minutes = planned_capacity
        # Keep the earliest slots schedulable; push the reserve to the day's tail.
        for index in free_indexes:
            slot = result[index]
            if allowed_free_minutes >= slot.minutes:
                allowed_free_minutes -= slot.minutes
                continue
            result[index] = Slot(
                id=slot.id,
                start_at=slot.start_at,
                end_at=slot.end_at,
                state=SlotState.BUFFER,
            )
    return result


def build_unique_slots(context: AvailabilityContext) -> tuple[Slot, ...]:
    counter = [0]
    slots: list[Slot] = []
    for window in context.availability_windows:
        slots.extend(_split_window(window, context.slot_minutes, counter))
    slots = _reserve_intervals(slots, context.fixed_event_intervals, SlotState.FIXED_EVENT)
    slots = _reserve_intervals(
        slots, context.protected_focus_blocks, SlotState.PROTECTED_FOCUS_BLOCK
    )
    slots = _apply_daily_capacity(
        slots,
        context.capacity_factor,
        context.slot_minutes,
        context.user_timezone,
    )
    return tuple(slots)


__all__ = [
    "AvailabilityContext",
    "Interval",
    "Slot",
    "SlotState",
    "build_unique_slots",
]
