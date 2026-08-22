from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from personal_pm_planner.availability.slots import AvailabilityContext, Interval, build_unique_slots
from personal_pm_planner.domain.availability import AvailabilityWindow, CalendarEventSnapshot
from personal_pm_planner.domain.enums import CalendarEventKind
from personal_pm_planner.domain.identifiers import CalendarEventId, WorkspaceId

WORKSPACE = WorkspaceId(UUID("00000000-0000-0000-0000-000000000001"))
DAY_START = datetime(2026, 8, 23, 9, 0, tzinfo=UTC)


def make_window(hours: int) -> AvailabilityWindow:
    return AvailabilityWindow(
        start_at=DAY_START,
        end_at=DAY_START + timedelta(hours=hours),
        tags=frozenset({"focus"}),
    )


@pytest.fixture
def fixed_event():
    return CalendarEventSnapshot(
        id=CalendarEventId(UUID(int=11)),
        workspace_id=WORKSPACE,
        title="회의",
        start_at=DAY_START + timedelta(hours=1),
        end_at=DAY_START + timedelta(hours=1, minutes=30),
        event_kind=CalendarEventKind.FIXED_BUSY,
        deadline_date=None,
        version=1,
    )


@pytest.fixture
def availability_case(fixed_event):
    """4h window, 30 min fixed meeting, factor 0.80 -> floor((210*0.8)/15)*15 = 165."""
    return (
        AvailabilityContext(
            availability_windows=(make_window(4),),
            calendar_events=(fixed_event,),
            slot_minutes=15,
            capacity_factor=0.80,
        ),
        fixed_event,
        165,
    )


def test_fixed_event_and_buffer_slots_are_not_free(availability_case) -> None:
    context, fixed_event, expected_capacity = availability_case
    slots = build_unique_slots(context)
    assert not any(slot.is_free and slot.overlaps_interval(fixed_event) for slot in slots)
    assert sum(slot.minutes for slot in slots if slot.state == "FREE") == expected_capacity


def test_every_slot_has_unique_id_and_one_state(availability_case) -> None:
    context, _, _ = availability_case
    slots = build_unique_slots(context)
    assert len({slot.id for slot in slots}) == len(slots)
    assert all(
        slot.state in {"FREE", "FIXED_EVENT", "PROTECTED_FOCUS_BLOCK", "BUFFER"} for slot in slots
    )


def test_slots_never_overlap_each_other(availability_case) -> None:
    context, _, _ = availability_case
    slots = build_unique_slots(context)
    ordered = sorted(slots, key=lambda item: item.start_at)
    for current, following in zip(ordered, ordered[1:], strict=False):
        assert not (current.start_at < following.end_at and following.start_at < current.end_at), (
            "slots must not overlap"
        )


def test_protected_focus_block_is_reserved() -> None:
    focus = Interval(
        start_at=DAY_START + timedelta(minutes=30),
        end_at=DAY_START + timedelta(minutes=60),
    )
    context = AvailabilityContext(
        availability_windows=(make_window(2),),
        protected_focus_blocks=(focus,),
    )
    slots = build_unique_slots(context)
    blocked = [slot for slot in slots if slot.state == "PROTECTED_FOCUS_BLOCK"]
    assert sum(slot.minutes for slot in blocked) == 30
    # raw free after reservations = 90 -> floor(90 * 0.80 / 15) * 15 = 60
    assert sum(slot.minutes for slot in slots if slot.state == "FREE") == 60


def test_low_condition_factor_reduces_free_capacity() -> None:
    context = AvailabilityContext(
        availability_windows=(make_window(2),),
        capacity_factor=0.65,
    )
    slots = build_unique_slots(context)
    assert sum(slot.minutes for slot in slots if slot.state == "FREE") == 75


def test_buffer_reserve_sits_after_free_capacity() -> None:
    context = AvailabilityContext(
        availability_windows=(make_window(2),),
        capacity_factor=0.65,
    )
    slots = build_unique_slots(context)
    free_slots = [slot for slot in slots if slot.state == "FREE"]
    buffer_slots = [slot for slot in slots if slot.state == "BUFFER"]
    assert free_slots and buffer_slots
    assert max(slot.end_at for slot in free_slots) <= min(slot.start_at for slot in buffer_slots)
