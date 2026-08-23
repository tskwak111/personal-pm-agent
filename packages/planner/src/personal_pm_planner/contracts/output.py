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
    status: str = "OK"
    external_warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.planner_version.strip():
            raise ValueError("planner_version must not be empty")
        if not self.input_hash.strip():
            raise ValueError("input_hash must not be empty")
        require_aware_utc(self.generated_at_utc)

    def canonical_core(self) -> dict[str, object]:
        """Stable comparable core used by reference vectors and replays."""
        return {
            "status": self.status,
            "base_allocations": [
                {
                    "task_id": item.task_id.value.hex,
                    "kind": item.kind,
                    "start": item.start_at.isoformat(),
                    "end": item.end_at.isoformat(),
                }
                for item in sorted(
                    self.base_plan.allocations if self.base_plan else (),
                    key=lambda x: (x.start_at, x.task_id.value.hex),
                )
            ],
            "today": {
                "core_result_task_id": (
                    self.today_plan.core_result_task_id.value.hex
                    if self.today_plan and self.today_plan.core_result_task_id
                    else None
                ),
                "must_do": [t.value.hex for t in self.today_plan.must_do]
                if self.today_plan
                else [],
            },
            "risks": [
                {
                    "milestone_id": risk.milestone_id.value.hex,
                    "level": risk.risk_level,
                    "base_coverage": risk.base_coverage,
                    "safety_coverage": risk.safety_coverage,
                }
                for risk in sorted(self.milestone_risks, key=lambda r: r.milestone_id.value.hex)
            ],
            "warnings": [*self.validation_warnings, *self.external_warnings],
        }

    @classmethod
    def invalid(
        cls,
        *,
        input_hash: str,
        generated_at_utc: datetime,
        warnings: tuple[str, ...],
        planner_version: str,
    ) -> "PlannerOutput":
        """A failed normalization never replaces the last valid plan."""
        return cls(
            planner_version=planner_version,
            input_hash=input_hash,
            generated_at_utc=generated_at_utc,
            base_plan=None,
            safety_plan=None,
            today_plan=None,
            milestone_risks=(),
            validation_warnings=warnings,
            status="INVALID_INPUT",
        )


__all__ = [
    "PassType",
    "TaskAllocation",
    "PlanPassResult",
    "TodayPlan",
    "MilestoneRisk",
    "PlannerOutput",
]
