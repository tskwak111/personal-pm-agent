"""Today plan assembly per Planner Spec section 13."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from personal_pm_planner.contracts.input import PlannerInput
from personal_pm_planner.domain.enums import TaskStatus
from personal_pm_planner.domain.identifiers import MilestoneId, TaskId
from personal_pm_planner.risk.classify import RiskLevel
from personal_pm_planner.scheduling.passes import PlanningPasses


class RiskAssessmentLike(Protocol):
    @property
    def milestone_id(self) -> MilestoneId: ...

    @property
    def risk_level(self) -> str: ...


@dataclass(frozen=True, slots=True)
class TodayPlanView:
    core_result_task_id: TaskId | None
    must_do: tuple[TaskId, ...]
    next_queue: tuple[TaskId, ...]
    opportunistic: tuple[TaskId, ...]
    excluded: tuple[TaskId, ...]
    warnings: tuple[str, ...] = field(default=())


def build_today_plan(
    value: PlannerInput,
    passes: PlanningPasses,
    risks: Mapping[MilestoneId, RiskAssessmentLike],
) -> TodayPlanView:
    """Derive the today view from the Base pass without inventing work.

    - ``반드시 완료`` lists only tasks whose base demand is fully allocated.
    - Capacity-excluded tasks appear explicitly in ``excluded``.
    """
    timezone = ZoneInfo(value.user_timezone)
    local_now_date = value.now_utc.astimezone(timezone).date()

    minutes_today: dict[TaskId, int] = {}
    for allocation in passes.base.allocations:
        if allocation.kind != "TASK":
            continue
        if allocation.start_at.astimezone(timezone).date() != local_now_date:
            continue
        minutes = int((allocation.end_at - allocation.start_at).total_seconds() // 60)
        minutes_today[allocation.task_id] = minutes_today.get(allocation.task_id, 0) + minutes

    active = [
        task for task in value.tasks if task.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
    ]
    from personal_pm_planner.domain.task import TaskSnapshot

    fully_allocated: list[TaskSnapshot] = []
    partial: list[TaskSnapshot] = []
    excluded: list[TaskSnapshot] = []
    for task in sorted(active, key=lambda item: item.id.value.hex):
        got = minutes_today.get(task.id, 0)
        if got <= 0:
            excluded.append(task)
        elif got >= task.remaining_base_minutes:
            fully_allocated.append(task)
        else:
            partial.append(task)

    # Core result prefers a completable P1-class hard-deadline task; the
    # enriched priority lives on allocations order, so use must-start ordering
    # from the base pass as the deterministic proxy.
    def start_key(task: TaskSnapshot) -> datetime:
        allocs = [
            allocation
            for allocation in passes.base.allocations
            if allocation.task_id is task.id and allocation.kind == "TASK"
        ]
        if not allocs:
            return datetime.max.replace(tzinfo=value.now_utc.tzinfo)
        return min(allocation.start_at for allocation in allocs)

    ordered_full = sorted(fully_allocated, key=start_key)
    core = ordered_full[0].id if ordered_full else None
    must_do = tuple(item.id for item in ordered_full[:3])
    core_result = must_do[0] if must_do else core

    critical_ids = {
        assessment.milestone_id.value
        for assessment in risks.values()
        if assessment.risk_level == RiskLevel.CRITICAL.value
    }
    warnings = tuple(f"milestone:{mid.hex}:CRITICAL" for mid in critical_ids)

    return TodayPlanView(
        core_result_task_id=core_result,
        must_do=must_do,
        next_queue=tuple(item.id for item in partial),
        opportunistic=(),
        excluded=tuple(item.id for item in excluded),
        warnings=warnings,
    )


__all__ = ["TodayPlanView", "build_today_plan"]
