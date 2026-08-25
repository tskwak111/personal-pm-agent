"""Approved-scope decomposition validation.

The LLM may only split the approved milestone into 30-120 minute tasks with
completion conditions; scope expansion and missing conditions are rejected
before anything reaches Planning Core.
"""

from __future__ import annotations

from dataclasses import dataclass


class ScopeExpansionError(Exception):
    def __init__(self) -> None:
        super().__init__("SCOPE_EXPANSION: deliverable differs from approved scope")


class InvalidTaskSizeError(Exception):
    def __init__(self, title: str, minutes: int) -> None:
        super().__init__(f"TASK_SIZE: {title} is {minutes} minutes (allowed 30-120)")


class MissingCompletionConditionError(Exception):
    def __init__(self, title: str) -> None:
        super().__init__(f"COMPLETION_CONDITION: {title} has no completion conditions")


@dataclass(frozen=True, slots=True)
class ApprovedMilestoneScope:
    milestone_id: str
    deliverable: str


@dataclass(frozen=True, slots=True)
class DecompositionTask:
    title: str
    base_duration_minutes: int
    completion_conditions: tuple[str, ...]
    depends_on: tuple[str, ...]
    outputs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DecompositionResult:
    deliverable: str
    tasks: tuple[DecompositionTask, ...]


def validate_decomposition(
    scope: ApprovedMilestoneScope, result: DecompositionResult
) -> None:
    if result.deliverable != scope.deliverable:
        raise ScopeExpansionError()
    for task in result.tasks:
        if not 30 <= task.base_duration_minutes <= 120:
            raise InvalidTaskSizeError(task.title, task.base_duration_minutes)
        if not task.completion_conditions:
            raise MissingCompletionConditionError(task.title)


__all__ = [
    "ApprovedMilestoneScope",
    "DecompositionResult",
    "DecompositionTask",
    "InvalidTaskSizeError",
    "MissingCompletionConditionError",
    "ScopeExpansionError",
    "validate_decomposition",
]
