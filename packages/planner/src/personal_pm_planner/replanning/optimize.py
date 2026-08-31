"""Lexicographic minimal-change replanning.

The "before" scenario keeps the prior plan shape by reserving its allocations
as protected capacity; the "after" scenario is the fresh deterministic plan.
Safety objectives precede change cost; protected items move only through
explicit proposals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from personal_pm_planner.availability.slots import Interval
from personal_pm_planner.contracts.input import PlannerInput, PriorAllocation
from personal_pm_planner.domain.enums import TaskStatus
from personal_pm_planner.domain.identifiers import MilestoneId, TaskId
from personal_pm_planner.replanning.cost import (
    ReplanMetrics,
    is_in_freeze_window,
    metrics_tuple,
    move_cost,
)
from personal_pm_planner.replanning.diff import ReplanDiff, diff_from_prior
from personal_pm_planner.risk.classify import (
    RiskAssessment,
    RiskContext,
    RiskLevel,
    calculate_risks,
)
from personal_pm_planner.scheduling.passes import PlanningPasses, run_planning_passes


@dataclass(frozen=True, slots=True)
class AppliedMove:
    task_id: TaskId
    old_start: datetime
    new_start: datetime
    cost: int


@dataclass(frozen=True, slots=True)
class ReplanOutcome:
    before: ReplanMetrics
    after: ReplanMetrics
    diff: ReplanDiff
    applied_moves: tuple[AppliedMove, ...]
    proposals: tuple[object, ...]
    selected_passes: PlanningPasses


def _prior_intervals(value: PlannerInput) -> tuple[Interval, ...]:
    snapshot = value.prior_plan_snapshot
    if snapshot is None:
        return ()
    return tuple(
        Interval(start_at=item.start_at, end_at=item.end_at) for item in snapshot.allocations
    )


def _protected_prior_allocations(value: PlannerInput) -> tuple[PriorAllocation, ...]:
    snapshot = value.prior_plan_snapshot
    if snapshot is None:
        return ()
    return tuple(
        item
        for item in snapshot.allocations
        if item.task_id in value.pinned_task_ids
        or is_in_freeze_window(item.start_at, value.now_utc)
    )


def _counts_by_level(
    risks: dict[MilestoneId, RiskAssessment],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for assessment in risks.values():
        level = str(assessment.risk_level)
        counts[level] = counts.get(level, 0) + 1
    return counts


def _metrics_from(
    value: PlannerInput,
    passes: PlanningPasses,
    risks: dict[MilestoneId, RiskAssessment],
    *,
    change_cost_total: int,
    authorization_violations: int,
) -> ReplanMetrics:
    counts = _counts_by_level(risks)
    base_demand = sum(
        task.remaining_base_minutes
        for task in value.tasks
        if task.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
    )
    safety_demand = sum(
        task.remaining_safety_minutes
        for task in value.tasks
        if task.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
    ) + sum(
        buffer.safety_duration_minutes
        for group in passes.buffers_by_milestone.values()
        for buffer in group
    )
    return ReplanMetrics(
        hard_constraint_violations=0,
        authorization_violations=authorization_violations,
        critical_milestones=counts.get(RiskLevel.CRITICAL.value, 0),
        base_unallocated_minutes=max(0, base_demand - passes.base.total_allocated_minutes),
        high_milestones=counts.get(RiskLevel.HIGH.value, 0),
        safety_unallocated_minutes=max(0, safety_demand - passes.safety.total_allocated_minutes),
        change_cost=change_cost_total,
        context_switches=0,
        energy_mismatch=0,
    )


@dataclass(frozen=True, slots=True)
class ReplanContext:
    """Explicit replanning inputs (kept for call-site clarity)."""

    value: PlannerInput

    @property
    def now_utc(self) -> datetime:
        return self.value.now_utc


def choose_candidate(candidates: tuple[ReplanMetrics, ...]) -> ReplanMetrics:
    """Lexicographic minimum over the normative field order."""
    return min(candidates, key=metrics_tuple)


def replan(value_or_context: PlannerInput | ReplanContext) -> ReplanOutcome:
    value = (
        value_or_context.value if isinstance(value_or_context, ReplanContext) else value_or_context
    )

    before_passes = run_planning_passes(value, extra_protected_intervals=_prior_intervals(value))
    before_risks = calculate_risks(before_passes, _risk_context(value))

    after_passes = run_planning_passes(value)
    after_risks = calculate_risks(after_passes, _risk_context(value))

    diff = diff_from_prior(value.prior_plan_snapshot, after_passes.base.allocations)

    pinned = set(value.pinned_task_ids)
    prior_start_by_task = {
        allocation.task_id: allocation.start_at
        for allocation in (
            value.prior_plan_snapshot.allocations if value.prior_plan_snapshot else []
        )
    }
    applied_moves: list[AppliedMove] = []
    proposals: list[object] = []
    change_cost_total = 0
    from personal_pm_planner.proposals.overload import proposal_for_disallowed_move

    for move in diff.moves:
        disallowed_reason: str | None = None
        if move.task_id in pinned:
            disallowed_reason = "USER_PINNED_MOVE_FORBIDDEN"
        elif move.prior_start is not None and is_in_freeze_window(move.prior_start, value.now_utc):
            disallowed_reason = "FREEZE_WINDOW_MOVE_FORBIDDEN"
        if disallowed_reason is not None:
            proposals.append(
                proposal_for_disallowed_move(
                    move.task_id,
                    reason_rule_id=disallowed_reason,
                    milestone_id=None,
                    minutes_delta=int(
                        (
                            move.new_start - prior_start_by_task.get(move.task_id, move.new_start)
                        ).total_seconds()
                        // 60
                    ),
                )
            )
            continue
        cost = move_cost(move.prior_start, move.new_start)
        applied_moves.append(
            AppliedMove(
                task_id=move.task_id,
                old_start=move.prior_start,
                new_start=move.new_start,
                cost=cost,
            )
        )
        change_cost_total += cost

    protected_prior = _protected_prior_allocations(value)
    protected_by_task = {item.task_id: item for item in protected_prior}
    for task_id in diff.removed_task_ids:
        protected = protected_by_task.get(task_id)
        if protected is None:
            continue
        reason = (
            "USER_PINNED_MOVE_FORBIDDEN" if task_id in pinned else "FREEZE_WINDOW_MOVE_FORBIDDEN"
        )
        proposals.append(
            proposal_for_disallowed_move(
                task_id,
                reason_rule_id=reason,
                milestone_id=None,
                minutes_delta=0,
            )
        )

    before_metrics = _metrics_from(
        value,
        before_passes,
        before_risks,
        change_cost_total=0,
        authorization_violations=0,
    )
    after_metrics = _metrics_from(
        value,
        after_passes,
        after_risks,
        change_cost_total=change_cost_total,
        authorization_violations=len(proposals),
    )

    return ReplanOutcome(
        before=before_metrics,
        after=after_metrics,
        diff=diff,
        applied_moves=tuple(applied_moves),
        proposals=tuple(proposals),
        selected_passes=(
            run_planning_passes(
                value,
                preallocated=protected_prior,
            )
            if proposals
            else after_passes
        ),
    )


def _risk_context(value: PlannerInput) -> RiskContext:
    from personal_pm_planner.risk.classify import build_risk_context

    return build_risk_context(value)


__all__ = ["AppliedMove", "ReplanContext", "ReplanOutcome", "choose_candidate", "replan"]
