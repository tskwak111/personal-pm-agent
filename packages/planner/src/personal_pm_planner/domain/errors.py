"""Typed planner domain errors with stable machine-readable codes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from personal_pm_planner.domain.dependency import DependencyCycle


class PlannerDomainError(Exception):
    """Base class for Planning Core domain rule violations."""

    code: str = "PLANNER_DOMAIN_ERROR"


class InvalidInputError(PlannerDomainError):
    code = "INVALID_INPUT"


class DependencyCycleError(PlannerDomainError):
    """A dependency graph contains at least one unresolved cycle."""

    code = "DEPENDENCY_CYCLE"

    def __init__(self, cycles: tuple[DependencyCycle, ...]) -> None:
        self.cycles = tuple(cycles)
        paths = ", ".join(
            "->".join(task_id.value.hex for task_id in cycle.task_ids) for cycle in self.cycles
        )
        super().__init__(f"dependency cycle detected: {paths}")
