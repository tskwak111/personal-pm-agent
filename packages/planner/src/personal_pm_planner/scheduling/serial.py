"""Serial schedule generation over unique slots.

Greedy earliest-feasible placement in caller-provided priority order. The
ledger guarantees exactly one owner per slot; dependency readiness and P0
promotion live in the passes orchestrator, keeping this module mechanical.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from personal_pm_planner.contracts.output import PassType, TaskAllocation
from personal_pm_planner.domain.identifiers import TaskId
from personal_pm_planner.scheduling.priority import SchedulableTask, priority_key

MAX_CHUNKS_PER_DAY = 3


@dataclass(frozen=True, slots=True)
class LedgerSlot:
    """Working copy of an availability slot inside one pass."""

    id: str
    start_at: datetime
    end_at: datetime
    is_free: bool
    owner: TaskId | None


class SlotLike(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def start_at(self) -> datetime: ...

    @property
    def end_at(self) -> datetime: ...

    @property
    def is_free(self) -> bool: ...


class SlotLedger:
    def __init__(self, slots: tuple[SlotLike, ...]) -> None:
        self._slots: list[LedgerSlot] = []
        for slot in sorted(slots, key=lambda item: item.start_at):
            self._slots.append(
                LedgerSlot(
                    id=slot.id,
                    start_at=slot.start_at,
                    end_at=slot.end_at,
                    is_free=slot.is_free,
                    owner=None,
                )
            )

    def free_slots(self) -> list[LedgerSlot]:
        return [slot for slot in self._slots if slot.is_free]

    def allocate(self, slot_ids: tuple[str, ...], owner: TaskId) -> None:
        claimed = set(slot_ids)
        self._slots = [
            (
                LedgerSlot(
                    id=slot.id,
                    start_at=slot.start_at,
                    end_at=slot.end_at,
                    is_free=False,
                    owner=owner,
                )
                if slot.id in claimed
                else slot
            )
            for slot in self._slots
        ]

    def owned_minutes(self, owner: TaskId) -> int:
        return sum(
            int((slot.end_at - slot.start_at).total_seconds() // 60)
            for slot in self._slots
            if slot.owner == owner
        )


def _contiguous_runs(slots: list[LedgerSlot]) -> list[list[LedgerSlot]]:
    runs: list[list[LedgerSlot]] = []
    current: list[LedgerSlot] = []
    for slot in slots:
        if not current:
            current = [slot]
            continue
        if current[-1].end_at == slot.start_at:
            current.append(slot)
        else:
            runs.append(current)
            current = [slot]
    if current:
        runs.append(current)
    return runs


def _run_minutes(run: list[LedgerSlot]) -> int:
    return sum(int((slot.end_at - slot.start_at).total_seconds() // 60) for slot in run)


class ScheduleResult:
    def __init__(
        self,
        allocations: tuple[TaskAllocation, ...],
        unallocated_task_ids: frozenset[TaskId],
        total_allocated_minutes: int,
        ledger: SlotLedger,
    ) -> None:
        self.allocations = allocations
        self.unallocated_task_ids = unallocated_task_ids
        self.total_allocated_minutes = total_allocated_minutes
        self.slot_ledger = ledger


def _place_task(
    ledger: SlotLedger,
    task: SchedulableTask,
    required_minutes: int,
    pass_type_str: str,
) -> list[TaskAllocation]:
    remaining = required_minutes
    allocations: list[TaskAllocation] = []
    chunk_index = 0
    day_chunks: dict[date, int] = {}
    earliest = task.start_after

    while remaining > 0:
        runs = [
            run
            for run in _contiguous_runs(ledger.free_slots())
            if earliest is None or run[-1].end_at > earliest
        ]
        placed_this_pass = False
        for run in runs:
            effective_start = run[0].start_at
            if earliest is not None and run[-1].end_at > earliest:
                effective_start = max(run[0].start_at, earliest)
            available = sum(
                int((slot.end_at - slot.start_at).total_seconds() // 60)
                for slot in run
                if slot.end_at > effective_start
            )
            if available <= 0:
                continue
            minimum_chunk = min(task.min_chunk_minutes, remaining)
            if available < minimum_chunk:
                continue
            if not task.splittable:
                if available < remaining:
                    continue
                take = remaining
            else:
                day = run[0].start_at.date()
                if day_chunks.get(day, 0) >= MAX_CHUNKS_PER_DAY:
                    continue
                take = min(available, remaining)

            selected: list[LedgerSlot] = []
            acc = 0
            for slot in run:
                if slot.end_at <= effective_start:
                    continue
                selected.append(slot)
                acc += int((slot.end_at - slot.start_at).total_seconds() // 60)
                if acc >= take:
                    break
            trimmed: list[LedgerSlot] = []
            acc = 0
            for slot in selected:
                trimmed.append(slot)
                acc += int((slot.end_at - slot.start_at).total_seconds() // 60)
                if acc >= take:
                    break
            slot_ids = tuple(slot.id for slot in trimmed)
            start = trimmed[0].start_at
            end = trimmed[-1].end_at
            ledger.allocate(slot_ids, task.id)
            allocations.append(
                TaskAllocation(
                    task_id=task.id,
                    pass_type=PassType(pass_type_str),
                    start_at=start,
                    end_at=end,
                    chunk_index=chunk_index,
                    kind="TASK",
                    source_slot_ids=slot_ids,
                )
            )
            chunk_index += 1
            day_chunks[start.date()] = day_chunks.get(start.date(), 0) + 1
            remaining -= acc
            placed_this_pass = True
            if remaining <= 0:
                break
        if not placed_this_pass:
            break

    return allocations


def serial_schedule(
    tasks: tuple[SchedulableTask, ...],
    slots: tuple[SlotLike, ...],
    duration_field: str,
    pass_type: str = "base",
) -> ScheduleResult:
    ledger = SlotLedger(slots)
    allocations: list[TaskAllocation] = []
    unallocated: set[TaskId] = set()
    total = 0

    ordered = sorted(tasks, key=priority_key)

    for task in ordered:
        required = getattr(task, duration_field)
        if required <= 0:
            continue
        produced = _place_task(ledger, task, required, PassType(pass_type))
        placed = sum(int((item.end_at - item.start_at).total_seconds() // 60) for item in produced)
        allocations.extend(produced)
        total += placed
        if placed < required:
            unallocated.add(task.id)

    return ScheduleResult(
        allocations=tuple(allocations),
        unallocated_task_ids=frozenset(unallocated),
        total_allocated_minutes=total,
        ledger=ledger,
    )


__all__ = ["ScheduleResult", "SlotLedger", "serial_schedule"]
