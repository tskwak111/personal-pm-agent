"""Frozen Planner output contract skeleton.

Phase 2 fills the planning results; this module fixes the stable shape and
canonical serialization rules so downstream consumers bind to one contract.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from personal_pm_planner.domain.identifiers import MilestoneId, TaskId
from personal_pm_planner.domain.time import require_aware_utc


class PassType(StrEnum):
    BASE = "base"
    SAFETY = "safety"


@dataclass(frozen=True, slots=True)
class TaskAllocation:
    task_id: TaskId
    pass_type: PassType
    start_at: datetime
    end_at: datetime
    chunk_index: int
    kind: str = "TASK"
    source_slot_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_aware_utc(self.start_at)
        require_aware_utc(self.end_at)
        if self.end_at <= self.start_at:
            raise ValueError("allocation end must be after start")
        if self.chunk_index < 0:
            raise ValueError("chunk_index must not be negative")


@dataclass(frozen=True, slots=True)
class PlanPassResult:
    pass_type: PassType
    allocations: tuple[TaskAllocation, ...]
    unallocated_base_minutes: int
    unallocated_safety_minutes: int


@dataclass(frozen=True, slots=True)
class TodayPlan:
    core_result_task_id: TaskId | None
    must_do: tuple[TaskId, ...]
    next_queue: tuple[TaskId, ...]
    opportunistic: tuple[TaskId, ...]
    excluded: tuple[TaskId, ...]


@dataclass(frozen=True, slots=True)
class MilestoneRisk:
    milestone_id: MilestoneId
    risk_level: str
    base_coverage: float | None
    safety_coverage: float | None
    slack_minutes: int | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlannerOutput:
    planner_version: str
    input_hash: str
    generated_at_utc: datetime
    base_plan: PlanPassResult | None
    safety_plan: PlanPassResult | None
    today_plan: TodayPlan | None
    milestone_risks: tuple[MilestoneRisk, ...]
    validation_warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.planner_version.strip():
            raise ValueError("planner_version must not be empty")
        if not self.input_hash.strip():
            raise ValueError("input_hash must not be empty")
        require_aware_utc(self.generated_at_utc)


__all__ = [
    "PassType",
    "TaskAllocation",
    "PlanPassResult",
    "TodayPlan",
    "MilestoneRisk",
    "PlannerOutput",
]
