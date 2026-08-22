"""Graph analysis: cycles, backward timing, handoff and demand."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from datetime import time as time_module
from zoneinfo import ZoneInfo

from personal_pm_planner.contracts.input import PlannerInput
from personal_pm_planner.domain.dependency import DependencyGraph
from personal_pm_planner.domain.enums import TaskStatus
from personal_pm_planner.domain.identifiers import MilestoneId, TaskId
from personal_pm_planner.domain.task import TaskSnapshot
from personal_pm_planner.domain.work import MilestoneSnapshot
from personal_pm_planner.graph.critical_path import (
    TaskTimingNode,
    backward_timing,
    unlock_counts,
)
from personal_pm_planner.graph.cycles import CycleReport
from personal_pm_planner.normalization.dates import effective_deadline


@dataclass(frozen=True, slots=True)
class ExternalDependencyRisk:
    external_dependency_id: object
    latest_safe_handoff_at: datetime | None
    expected_delivery_at: datetime | None
    fallback_available: bool


@dataclass(frozen=True, slots=True)
class GraphAnalysis:
    blocked_task_ids: frozenset[TaskId]
    cycles: tuple[CycleReport, ...]
    must_start_by_at: dict[TaskId, datetime]
    critical_path_unlock_count: dict[TaskId, int]
    required_demand_minutes: int
    external_dependencies: tuple[ExternalDependencyRisk, ...]

    def ready_to_schedule(self, task_id: TaskId) -> bool:
        return task_id not in self.blocked_task_ids


def build_graph_analysis(value: PlannerInput) -> GraphAnalysis:
    graph = DependencyGraph.from_dependencies(list(value.task_dependencies))
    cycle_reports = tuple(CycleReport.from_cycle(cycle) for cycle in graph.cycles())
    blocked = frozenset(task_id for report in cycle_reports for task_id in report.task_ids)

    nodes: dict[TaskId, TaskTimingNode] = {}
    milestone_limits: dict[MilestoneId, datetime] = {}
    for milestone in value.milestones:
        result = effective_deadline(milestone, value.user_timezone)
        if result.instant is None:
            continue
        limit = result.instant
        if deadline_type_is_buffered(milestone):
            from datetime import timedelta

            limit = limit - timedelta(minutes=milestone.required_buffer_minutes)
        milestone_limits[milestone.id] = limit

    schedulable_statuses = (
        TaskStatus.DRAFT,
        TaskStatus.PLANNED,
        TaskStatus.READY,
        TaskStatus.IN_PROGRESS,
        TaskStatus.WAITING,
        TaskStatus.BLOCKED,
        TaskStatus.DEFERRED,
    )
    demand = 0
    for task in value.tasks:
        active = task.status in schedulable_statuses
        if active:
            demand += task.safety_duration_minutes
        task_deadline = effective_deadline_from_task(task, value.user_timezone)
        nodes[task.id] = TaskTimingNode(
            task_id=task.id,
            safety_duration_minutes=task.safety_duration_minutes,
            status=task.status,
            milestone_id=task.milestone_id,
            effective_deadline_at=task_deadline,
        )

    timing = backward_timing(
        nodes=nodes,
        graph=graph,
        milestone_limits=milestone_limits,
        fallback_horizon=value.horizon_end_utc,
    )
    counts = unlock_counts(nodes, graph)

    external_risks: list[ExternalDependencyRisk] = []
    for external in value.external_dependencies:
        handoffs = [
            timing.must_start_by(affected)
            for affected in external.affected_task_ids
            if affected in timing.must_start_by_at
        ]
        known_handoffs = [instant for instant in handoffs if instant is not None]
        latest_safe = min(known_handoffs) if known_handoffs else None
        external_risks.append(
            ExternalDependencyRisk(
                external_dependency_id=external.id,
                latest_safe_handoff_at=latest_safe,
                expected_delivery_at=external.expected_delivery_at,
                fallback_available=external.fallback_available,
            )
        )

    return GraphAnalysis(
        blocked_task_ids=blocked,
        cycles=cycle_reports,
        must_start_by_at=dict(timing.must_start_by_at),
        critical_path_unlock_count=counts,
        required_demand_minutes=demand,
        external_dependencies=tuple(external_risks),
    )


def deadline_type_is_buffered(milestone: MilestoneSnapshot) -> bool:
    return milestone.required_buffer_minutes > 0 and (
        milestone.deadline_time_known or milestone.deadline_date_known
    )


def effective_deadline_from_task(
    task: TaskSnapshot,
    user_timezone: str,
) -> datetime | None:
    """Tasks mirror the milestone date-only rule: local midnight boundary."""
    if task.deadline_time_known and task.deadline_at is not None:
        return task.deadline_at.astimezone(UTC)
    if task.deadline_date is not None:
        tz = ZoneInfo(user_timezone)
        local_midnight = datetime.combine(task.deadline_date, time_module(0, 0), tzinfo=tz)
        return local_midnight.astimezone(UTC)
    return None
