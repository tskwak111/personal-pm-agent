"""Priority classes and the normative stable tie-breaking tuple.

The weighted score is explanatory only; selection order is this tuple,
compared lexicographically, with task id as the final tie break.
LLM scores never participate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

from personal_pm_planner.domain.enums import DeadlineType, ImportanceLevel
from personal_pm_planner.domain.identifiers import TaskId


class PriorityClass(IntEnum):
    P0 = 0  # Rescue
    P1 = 1  # Protect
    P2 = 2  # Progress
    P3 = 3  # Maintain
    P4 = 4  # Optional


IMPORTANCE_RANK = {
    ImportanceLevel.PROTECTED: 0,
    ImportanceLevel.IMPORTANT: 1,
    ImportanceLevel.NORMAL: 2,
    ImportanceLevel.OPTIONAL: 3,
    ImportanceLevel.ON_HOLD: 4,
}


@dataclass(frozen=True, slots=True)
class PriorityContext:
    now_utc: datetime


@dataclass(frozen=True, slots=True)
class SchedulableTask:
    id: TaskId
    priority_class: PriorityClass
    must_start_by_at: datetime | None
    effective_deadline_at: datetime | None
    critical_path_unlock_count: int
    external_commitment: bool
    user_importance: ImportanceLevel
    prior_plan_position: int | None
    context_switch_penalty: int
    created_at: datetime
    llm_score: float | None = None
    base_duration_minutes: int = 0
    safety_duration_minutes: int = 0
    splittable: bool = True
    min_chunk_minutes: int = 30
    start_after: datetime | None = None


def initial_priority_class(
    *,
    verified_deadline_passed: bool,
    deadline_type: DeadlineType,
    importance: ImportanceLevel,
    is_synthetic_buffer: bool = False,
    is_routine: bool = False,
    is_exploration: bool = False,
) -> PriorityClass:
    if verified_deadline_passed:
        return PriorityClass.P0
    if is_synthetic_buffer:
        return PriorityClass.P1
    if deadline_type in (DeadlineType.HARD_DEADLINE, DeadlineType.EXTERNAL_COMMITMENT):
        return PriorityClass.P1
    if is_routine:
        return PriorityClass.P3
    if is_exploration or importance in (ImportanceLevel.OPTIONAL, ImportanceLevel.ON_HOLD):
        return PriorityClass.P4
    return PriorityClass.P2


def priority_key(
    task: SchedulableTask,
    priority_context: PriorityContext | None = None,
) -> tuple[object, ...]:
    del priority_context  # kept for call-site symmetry; key uses task fields only
    return (
        int(task.priority_class),
        task.must_start_by_at or datetime.max.replace(tzinfo=task.created_at.tzinfo),
        task.effective_deadline_at or datetime.max.replace(tzinfo=task.created_at.tzinfo),
        -task.critical_path_unlock_count,
        -int(task.external_commitment),
        IMPORTANCE_RANK[task.user_importance],
        task.prior_plan_position if task.prior_plan_position is not None else 2**63 - 1,
        task.context_switch_penalty,
        task.created_at,
        task.id.value.hex,
    )
