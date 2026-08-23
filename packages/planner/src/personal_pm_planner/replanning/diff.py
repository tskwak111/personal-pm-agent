"""Prior-plan versus candidate-plan differences."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from personal_pm_planner.contracts.input import PriorPlanSnapshot
from personal_pm_planner.domain.identifiers import TaskId


class TaskAllocationLike(Protocol):
    @property
    def task_id(self) -> TaskId: ...

    @property
    def kind(self) -> str: ...

    @property
    def start_at(self) -> datetime: ...

    @property
    def end_at(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class MoveRecord:
    task_id: TaskId
    prior_start: datetime
    new_start: datetime
    kind: str  # "MOVE" or "EXTEND"


@dataclass(frozen=True, slots=True)
class ReplanDiff:
    changed_task_count: int
    moves: tuple[MoveRecord, ...] = field(default=())
    removed_task_ids: tuple[TaskId, ...] = field(default=())


def diff_from_prior(
    prior: PriorPlanSnapshot | None,
    current_allocations: tuple[TaskAllocationLike, ...],
) -> ReplanDiff:
    """Compare the prior snapshot against the candidate's TASK allocations."""
    current_by_task: dict[TaskId, list[TaskAllocationLike]] = {}
    for allocation in current_allocations:
        if allocation.kind != "TASK":
            continue
        current_by_task.setdefault(allocation.task_id, []).append(allocation)

    moves: list[MoveRecord] = []
    removed: list[TaskId] = []
    if prior is None:
        return ReplanDiff(changed_task_count=0, moves=(), removed_task_ids=())

    for prior_allocation in prior.allocations:
        task_id = prior_allocation.task_id
        candidates = current_by_task.get(task_id)
        if not candidates:
            removed.append(task_id)
            continue
        first = sorted(candidates, key=lambda item: item.start_at)[0]
        same_start = first.start_at == prior_allocation.start_at
        covers_prior_end = first.end_at >= prior_allocation.end_at
        if same_start and covers_prior_end and len(candidates) == 1:
            # Unchanged (or a pure extension of the same block keeps identity).
            if first.end_at == prior_allocation.end_at:
                continue
            moves.append(
                MoveRecord(
                    task_id=task_id,
                    prior_start=prior_allocation.start_at,
                    new_start=first.start_at,
                    kind="EXTEND",
                )
            )
        else:
            moves.append(
                MoveRecord(
                    task_id=task_id,
                    prior_start=prior_allocation.start_at,
                    new_start=first.start_at,
                    kind="MOVE",
                )
            )

    return ReplanDiff(
        changed_task_count=len(moves) + len(removed),
        moves=tuple(moves),
        removed_task_ids=tuple(removed),
    )


__all__ = ["MoveRecord", "ReplanDiff", "diff_from_prior"]
