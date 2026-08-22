"""Explicit Task state machine.

Transitions follow `docs/architecture/domain-state-machines.md`; the planner
package encodes them as pure data so every caller enforces the same contract.
"""

from dataclasses import replace

from personal_pm_planner.domain.enums import TaskStatus
from personal_pm_planner.domain.task import TaskSnapshot

ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.DRAFT: frozenset({TaskStatus.PLANNED, TaskStatus.CANCELLED}),
    TaskStatus.PLANNED: frozenset({TaskStatus.READY, TaskStatus.DEFERRED, TaskStatus.CANCELLED}),
    TaskStatus.READY: frozenset(
        {
            TaskStatus.IN_PROGRESS,
            TaskStatus.WAITING,
            TaskStatus.BLOCKED,
            TaskStatus.DEFERRED,
        }
    ),
    TaskStatus.IN_PROGRESS: frozenset(
        {TaskStatus.DONE, TaskStatus.WAITING, TaskStatus.BLOCKED, TaskStatus.READY}
    ),
    TaskStatus.WAITING: frozenset({TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.BLOCKED: frozenset({TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.DONE: frozenset({TaskStatus.IN_PROGRESS}),
    TaskStatus.DEFERRED: frozenset({TaskStatus.PLANNED, TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.CANCELLED: frozenset({TaskStatus.PLANNED}),
}


def transition_task(
    task: TaskSnapshot,
    target: TaskStatus,
    *,
    waiting_resolved: bool = False,
    blocker_resolved: bool = False,
    completion_confirmed: bool = False,
    waiting_reason: str | None = None,
) -> TaskSnapshot:
    """Return a new snapshot with *target* status or raise ValueError."""
    if target not in ALLOWED_TRANSITIONS[task.status]:
        raise ValueError(f"transition {task.status.value} -> {target.value} is not allowed")
    if task.status is TaskStatus.WAITING and target is TaskStatus.READY:
        if not waiting_resolved:
            raise ValueError("waiting condition must be resolved before Ready")
    if task.status is TaskStatus.BLOCKED and target is TaskStatus.READY:
        if not blocker_resolved:
            raise ValueError("blocker must be resolved before Ready")
    if target is TaskStatus.DONE:
        if not completion_confirmed:
            raise ValueError("DONE requires completion confirmation")
        if task.remaining_base_minutes != 0 or task.remaining_safety_minutes != 0:
            raise ValueError("remaining work must reach zero before DONE")

    next_reason = task.waiting_reason
    if target is TaskStatus.WAITING:
        next_reason = (waiting_reason or task.waiting_reason or "").strip() or None
        if not next_reason:
            raise ValueError("waiting reason required to enter waiting")
    elif task.status is TaskStatus.WAITING:
        next_reason = None

    if target is TaskStatus.CANCELLED:
        # Cancelling removes any remaining executable scope.
        return replace(
            task,
            status=target,
            waiting_reason=next_reason,
            remaining_base_minutes=0,
            remaining_safety_minutes=0,
            version=task.version + 1,
        )
    return replace(task, status=target, waiting_reason=next_reason, version=task.version + 1)
