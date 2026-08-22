"""Cycle reports for planner output."""

from __future__ import annotations

from dataclasses import dataclass

from personal_pm_planner.domain.dependency import DependencyCycle
from personal_pm_planner.domain.identifiers import TaskId


@dataclass(frozen=True, slots=True)
class CycleReport:
    task_ids: tuple[TaskId, ...]
    rule_id: str = "DEPENDENCY_CYCLE"

    @classmethod
    def from_cycle(cls, cycle: DependencyCycle) -> CycleReport:
        return cls(task_ids=tuple(cycle.task_ids))
