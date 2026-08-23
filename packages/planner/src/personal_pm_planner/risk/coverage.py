"""Coverage and slack derived from global Base/Safety allocations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from personal_pm_planner.contracts.input import PlannerInput
from personal_pm_planner.domain.enums import TaskStatus
from personal_pm_planner.domain.identifiers import MilestoneId, TaskId
from personal_pm_planner.domain.task import TaskSnapshot
from personal_pm_planner.graph.build import GraphAnalysis
from personal_pm_planner.normalization.dates import effective_deadline
from personal_pm_planner.scheduling.passes import PlanningPasses
from personal_pm_planner.scheduling.serial import ScheduleResult


@dataclass(frozen=True, slots=True)
class MilestoneCoverage:
    milestone_id: MilestoneId
    base_required_minutes: int
    safety_required_minutes: int
    base_allocated_minutes: int
    safety_allocated_minutes: int
    buffers_allocated_minutes: int
    buffer_required_minutes: int
    deadline_limit: datetime | None
    date_only: bool
    has_cycle_member: bool

    @property
    def base_coverage(self) -> float:
        if self.base_required_minutes <= 0:
            return 1.0
        return self.base_allocated_minutes / self.base_required_minutes

    @property
    def safety_coverage(self) -> float:
        total = self.safety_required_minutes + self.buffer_required_minutes
        if total <= 0:
            return 1.0
        return (self.safety_allocated_minutes + self.buffers_allocated_minutes) / total

    @property
    def unallocated_safety_minutes(self) -> int:
        total = self.safety_required_minutes + self.buffer_required_minutes
        return max(0, total - self.safety_allocated_minutes - self.buffers_allocated_minutes)


def _allocation_minutes_before(
    result: ScheduleResult,
    members: set[TaskId],
    limit: datetime | None,
) -> int:
    total = 0
    for allocation in result.allocations:
        if allocation.task_id not in members:
            continue
        if allocation.kind != "TASK" and not allocation.kind.endswith("_BUFFER"):
            continue
        if limit is None or allocation.end_at <= limit:
            minutes = int((allocation.end_at - allocation.start_at).total_seconds() // 60)
            total += minutes
    return total


def free_slack_after_pass(
    value: PlannerInput,
    passes: PlanningPasses,
    limit: datetime | None,
) -> int:
    """Usable FREE slot minutes between now and the deadline limit."""
    if limit is None or limit <= value.now_utc:
        return 0
    total = 0
    for slot in passes.safety.slot_ledger.free_slots():
        if slot.start_at >= value.now_utc and slot.end_at <= limit:
            total += int((slot.end_at - slot.start_at).total_seconds() // 60)
    return total


def milestone_coverages(
    value: PlannerInput,
    passes: PlanningPasses,
    analysis: GraphAnalysis,
) -> list[MilestoneCoverage]:
    tasks_by_milestone: dict[MilestoneId | None, list[TaskSnapshot]] = {}
    task_by_id = {}
    for task in value.tasks:
        if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
            continue
        tasks_by_milestone.setdefault(task.milestone_id, []).append(task)
        task_by_id[task.id] = task

    coverages: list[MilestoneCoverage] = []
    for milestone in value.milestones:
        members = {task.id for task in tasks_by_milestone.get(milestone.id, [])}
        member_tasks = tasks_by_milestone.get(milestone.id, [])
        deadline = effective_deadline(milestone, value.user_timezone)
        base_required = sum(task.remaining_base_minutes for task in member_tasks)
        safety_required = sum(task.remaining_safety_minutes for task in member_tasks)

        buffers = passes.buffers_by_milestone.get(milestone.id, ())
        buffer_ids = {buffer.id for buffer in buffers}
        buffer_required = sum(buffer.safety_duration_minutes for buffer in buffers)
        buffers_allocated = _allocation_minutes_before(passes.safety, buffer_ids, deadline.instant)

        base_allocated = _allocation_minutes_before(passes.base, members, deadline.instant)
        # Buffer allocations carry their own synthetic ids, which never appear
        # in `members`; no subtraction is needed.
        safety_allocated = _allocation_minutes_before(passes.safety, members, deadline.instant)
        has_cycle_member = any(task_id in analysis.blocked_task_ids for task_id in members)
        coverages.append(
            MilestoneCoverage(
                milestone_id=milestone.id,
                base_required_minutes=base_required,
                safety_required_minutes=safety_required,
                base_allocated_minutes=base_allocated,
                safety_allocated_minutes=safety_allocated,
                buffers_allocated_minutes=buffers_allocated,
                buffer_required_minutes=buffer_required,
                deadline_limit=deadline.instant,
                date_only=milestone.deadline_date_known and not milestone.deadline_time_known,
                has_cycle_member=has_cycle_member,
            )
        )
    return coverages
