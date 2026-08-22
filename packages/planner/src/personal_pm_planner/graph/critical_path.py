"""Backward critical-path timing over Blocks Start edges."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from personal_pm_planner.domain.dependency import DependencyGraph
from personal_pm_planner.domain.enums import TaskStatus
from personal_pm_planner.domain.identifiers import MilestoneId, TaskId


@dataclass(frozen=True, slots=True)
class TaskTimingNode:
    task_id: TaskId
    safety_duration_minutes: int
    status: TaskStatus
    milestone_id: MilestoneId | None
    effective_deadline_at: datetime | None


@dataclass(frozen=True, slots=True)
class TimingResult:
    latest_finish_at: dict[TaskId, datetime]
    must_start_by_at: dict[TaskId, datetime]

    def must_start_by(self, task_id: TaskId) -> datetime | None:
        return self.must_start_by_at.get(task_id)


def backward_timing(
    nodes: dict[TaskId, TaskTimingNode],
    graph: DependencyGraph,
    *,
    milestone_limits: dict[MilestoneId, datetime],
    fallback_horizon: datetime,
) -> TimingResult:
    """Compute latest finish/start per task without touching cycle members."""
    latest_finish: dict[TaskId, datetime] = {}
    memo_start: dict[TaskId, datetime] = {}
    visiting: set[TaskId] = set()

    def successor_ids(task_id: TaskId) -> list[TaskId]:
        active = []
        for successor in sorted(graph.start_successors(task_id), key=lambda item: item.value.hex):
            node = nodes.get(successor)
            if node is None or node.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
                continue
            active.append(successor)
        return active

    def resolve(task_id: TaskId) -> datetime:
        if task_id in memo_start:
            return memo_start[task_id]
        if task_id in visiting:
            # Cycle member: timing is undefined; fall back to the horizon.
            return fallback_horizon
        visiting.add(task_id)
        node = nodes[task_id]
        limits: list[datetime] = [fallback_horizon]
        if node.effective_deadline_at is not None:
            limits.append(node.effective_deadline_at)
        if node.milestone_id is not None and node.milestone_id in milestone_limits:
            limits.append(milestone_limits[node.milestone_id])
        for successor in successor_ids(task_id):
            # A predecessor must finish before its successor can *start*.
            successor_start_limit = resolve(successor) - timedelta(
                minutes=nodes[successor].safety_duration_minutes
            )
            limits.append(successor_start_limit)
        latest_finish_value = min(limits)
        memo_start[task_id] = latest_finish_value
        latest_finish[task_id] = latest_finish_value
        visiting.discard(task_id)
        return latest_finish_value

    for task_id in sorted(nodes, key=lambda item: item.value.hex):
        resolve(task_id)

    must_start_by = {
        task_id: latest_finish[task_id] - timedelta(minutes=node.safety_duration_minutes)
        for task_id, node in nodes.items()
        if task_id in latest_finish
    }
    return TimingResult(latest_finish_at=latest_finish, must_start_by_at=must_start_by)


def unlock_counts(nodes: dict[TaskId, TaskTimingNode], graph: DependencyGraph) -> dict[TaskId, int]:
    counts: dict[TaskId, int] = {}
    for task_id, node in nodes.items():
        if node.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
            counts[task_id] = 0
            continue
        counts[task_id] = sum(
            1
            for successor in graph.start_successors(task_id)
            if nodes.get(successor) is not None
            and nodes[successor].status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
        )
    return counts
