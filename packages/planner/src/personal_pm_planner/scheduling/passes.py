"""Provisional, Base and Safety planning passes.

Two-stage class confirmation per Planner Spec section 9.0: run a provisional
Base pass, promote infeasible required paths to P0 exactly once, then execute
the final Base and Safety passes over independent slot ledgers. Mandatory
review/submission buffers are synthetic tasks that consume real slots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from personal_pm_planner.availability.slots import (
    AvailabilityContext,
    Interval,
    build_unique_slots,
)
from personal_pm_planner.contracts.input import PlannerInput
from personal_pm_planner.domain.enums import DeadlineType, ImportanceLevel, TaskStatus
from personal_pm_planner.domain.identifiers import MilestoneId, TaskId
from personal_pm_planner.domain.task import TaskSnapshot
from personal_pm_planner.graph.build import GraphAnalysis, build_graph_analysis
from personal_pm_planner.normalization.dates import effective_deadline
from personal_pm_planner.scheduling.priority import (
    PriorityClass,
    SchedulableTask,
    initial_priority_class,
)
from personal_pm_planner.scheduling.serial import ScheduleResult, SlotLike, serial_schedule


@dataclass(frozen=True, slots=True)
class PlanningPasses:
    provisional: ScheduleResult
    base: ScheduleResult
    safety: ScheduleResult
    promoted_task_count: int
    buffers_by_milestone: dict[MilestoneId, tuple[SchedulableTask, ...]] = field(
        default_factory=dict
    )


def _verified_deadline_passed(task: TaskSnapshot, now_utc: datetime) -> bool:
    if task.deadline_time_known and task.deadline_at is not None:
        return task.deadline_at <= now_utc
    # Date-only deadlines never become past-due facts before the next local day;
    # conservative handling treats them as not yet passed here (risk layer owns urgency).
    return False


def _deadline_type_for(
    task: TaskSnapshot,
    milestone_types: dict[MilestoneId, DeadlineType],
) -> DeadlineType:
    if task.milestone_id is not None:
        deadline_type = milestone_types.get(task.milestone_id)
        if deadline_type is not None:
            return deadline_type
    return DeadlineType.SOFT_GOAL


def enrich_tasks(
    value: PlannerInput,
    analysis: GraphAnalysis,
) -> tuple[SchedulableTask, ...]:
    milestone_types = {milestone.id: milestone.deadline_type for milestone in value.milestones}
    external_affected = {
        task_id
        for external in value.external_dependencies
        for task_id in external.affected_task_ids
    }
    prior_positions = _prior_positions(value)

    enriched: list[SchedulableTask] = []
    for task in value.tasks:
        if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
            continue
        priority_class = initial_priority_class(
            verified_deadline_passed=_verified_deadline_passed(task, value.now_utc),
            deadline_type=_deadline_type_for(task, milestone_types),
            importance=ImportanceLevel.NORMAL,
        )
        enriched.append(
            SchedulableTask(
                id=task.id,
                priority_class=priority_class,
                must_start_by_at=analysis.must_start_by_at.get(task.id),
                effective_deadline_at=(
                    task.deadline_at
                    if task.deadline_time_known and task.deadline_at is not None
                    else None
                ),
                critical_path_unlock_count=analysis.critical_path_unlock_count.get(task.id, 0),
                external_commitment=task.id in external_affected,
                user_importance=ImportanceLevel.NORMAL,
                prior_plan_position=prior_positions.get(task.id),
                context_switch_penalty=1,
                created_at=value.now_utc,
                base_duration_minutes=task.remaining_base_minutes,
                safety_duration_minutes=task.remaining_safety_minutes,
                splittable=task.splittable,
                min_chunk_minutes=task.min_chunk_minutes,
                start_after=task.start_after,
            )
        )
    return tuple(enriched)


def _prior_positions(value: PlannerInput) -> dict[TaskId, int]:
    snapshot = value.prior_plan_snapshot
    if snapshot is None:
        return {}
    positions: dict[TaskId, int] = {}
    for index, allocation in enumerate(snapshot.allocations):
        positions.setdefault(allocation.task_id, index)
    return positions


def create_synthetic_buffers(
    value: PlannerInput,
) -> dict[MilestoneId, tuple[SchedulableTask, ...]]:
    buffers_by_milestone: dict[MilestoneId, list[SchedulableTask]] = {}
    for milestone in value.milestones:
        limit = effective_deadline(milestone, value.user_timezone).instant
        total = milestone.required_buffer_minutes
        if limit is None or total <= 0:
            continue
        review_minutes = -(-total // 2)  # ceil half
        submission_minutes = total - review_minutes
        for kind, minutes in (
            ("REVIEW_BUFFER", review_minutes),
            ("SUBMISSION_BUFFER", submission_minutes),
        ):
            if minutes <= 0:
                continue
            buffers_by_milestone.setdefault(milestone.id, []).append(
                SchedulableTask(
                    id=TaskId(uuid5(NAMESPACE_URL, f"buffer:{milestone.id.value.hex}:{kind}")),
                    priority_class=PriorityClass.P1,
                    must_start_by_at=limit,
                    effective_deadline_at=limit,
                    critical_path_unlock_count=0,
                    external_commitment=False,
                    user_importance=ImportanceLevel.PROTECTED,
                    prior_plan_position=None,
                    context_switch_penalty=0,
                    created_at=value.now_utc,
                    base_duration_minutes=minutes,
                    safety_duration_minutes=minutes,
                    splittable=False,
                    min_chunk_minutes=min(minutes, 30),
                    kind=kind,
                )
            )
    return {mid: tuple(items) for mid, items in buffers_by_milestone.items()}


def _fresh_slots(
    value: PlannerInput,
    extra_protected_intervals: tuple[Interval, ...] = (),
) -> tuple[SlotLike, ...]:
    context = AvailabilityContext(
        availability_windows=value.availability_windows,
        calendar_events=value.calendar_events,
        protected_focus_blocks=extra_protected_intervals,
        slot_minutes=value.slot_minutes,
        capacity_factor=0.80,
        user_timezone=value.user_timezone,
    )
    return build_unique_slots(context)


def _is_required(deadline_type: DeadlineType) -> bool:
    return deadline_type in (DeadlineType.HARD_DEADLINE, DeadlineType.EXTERNAL_COMMITMENT)


def run_planning_passes(
    value: PlannerInput,
    *,
    extra_protected_intervals: tuple[Interval, ...] = (),
) -> PlanningPasses:
    analysis = build_graph_analysis(value)
    tasks = enrich_tasks(value, analysis)
    buffers_by_milestone = create_synthetic_buffers(value)
    buffer_tasks = tuple(buffer for group in buffers_by_milestone.values() for buffer in group)
    schedulable = tasks + buffer_tasks

    provisional = serial_schedule(
        tasks=schedulable,
        slots=_fresh_slots(value, extra_protected_intervals),
        duration_field="base_duration_minutes",
        pass_type="base",
    )
    final_tasks, promoted = _promote_infeasible_required_paths_once(schedulable, provisional, value)

    base = serial_schedule(
        tasks=final_tasks,
        slots=_fresh_slots(value, extra_protected_intervals),
        duration_field="base_duration_minutes",
        pass_type="base",
    )
    safety = serial_schedule(
        tasks=final_tasks,
        slots=_fresh_slots(value, extra_protected_intervals),
        duration_field="safety_duration_minutes",
        pass_type="safety",
    )
    return PlanningPasses(
        provisional=provisional,
        base=base,
        safety=safety,
        promoted_task_count=promoted,
        buffers_by_milestone=buffers_by_milestone,
    )


def _promote_infeasible_required_paths_once(
    tasks: tuple[SchedulableTask, ...],
    provisional: ScheduleResult,
    value: PlannerInput,
) -> tuple[tuple[SchedulableTask, ...], int]:
    """Promote unallocated required tasks to P0 exactly once."""
    milestone_types = {milestone.id: milestone.deadline_type for milestone in value.milestones}
    milestone_by_task = {task.id: task.milestone_id for task in value.tasks}
    promoted = 0
    updated: list[SchedulableTask] = []
    for task in tasks:
        if (
            task.kind == "TASK"
            and task.priority_class is not PriorityClass.P0
            and task.id in provisional.unallocated_task_ids
        ):
            milestone_ref = milestone_by_task.get(task.id)
            deadline_type = (
                milestone_types.get(milestone_ref, DeadlineType.SOFT_GOAL)
                if milestone_ref is not None
                else DeadlineType.SOFT_GOAL
            )
            if _is_required(deadline_type):
                promoted += 1
                fields = {
                    name: getattr(task, name) for name in SchedulableTask.__dataclass_fields__
                }
                fields["priority_class"] = PriorityClass.P0
                updated.append(SchedulableTask(**fields))
                continue
        updated.append(task)
    return tuple(updated), promoted
