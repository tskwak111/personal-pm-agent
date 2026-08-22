"""Contract validation for planner input.

Validation failures return typed results with stable Rule IDs; they never
mutate or discard the prior valid plan snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass

from personal_pm_planner.contracts.input import PlannerInput, PriorPlanSnapshot
from personal_pm_planner.domain.enums import TaskStatus
from personal_pm_planner.normalization.canonical import hash_canonical_input


@dataclass(frozen=True, slots=True)
class ContractViolation:
    rule_id: str
    detail: str


@dataclass(frozen=True, slots=True)
class ValidPlannerInput:
    value: PlannerInput
    input_hash: str


@dataclass(frozen=True, slots=True)
class InvalidPlannerInput:
    error_code: str
    rule_ids: tuple[str, ...]
    prior_plan_snapshot: PriorPlanSnapshot | None


NormalizationResult = ValidPlannerInput | InvalidPlannerInput


def validate_contract(value: PlannerInput) -> tuple[ContractViolation, ...]:
    violations: list[ContractViolation] = []
    for task in value.tasks:
        if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED) and (
            task.remaining_base_minutes > 0 or task.remaining_safety_minutes > 0
        ):
            violations.append(
                ContractViolation(
                    rule_id="DONE_TASK_HAS_REMAINING_TIME",
                    detail=(
                        f"task {task.id.value.hex} is {task.status.value}"
                        " with remaining minutes"
                    ),
                )
            )
        if task.base_duration_minutes <= 0:
            violations.append(
                ContractViolation(
                    rule_id="BASE_DURATION_NOT_POSITIVE",
                    detail=f"task {task.id.value.hex}",
                )
            )
        if task.safety_duration_minutes < task.base_duration_minutes:
            violations.append(
                ContractViolation(
                    rule_id="SAFETY_DURATION_BELOW_BASE",
                    detail=f"task {task.id.value.hex}",
                )
            )
    known_task_ids = {task.id for task in value.tasks}
    for item in value.task_dependencies:
        if item.predecessor_id not in known_task_ids or item.successor_id not in known_task_ids:
            violations.append(
                ContractViolation(
                    rule_id="DEPENDENCY_REFERENCES_UNKNOWN_TASK",
                    detail=f"{item.predecessor_id.value.hex}->{item.successor_id.value.hex}",
                )
            )
    for external in value.external_dependencies:
        if any(task_id not in known_task_ids for task_id in external.affected_task_ids):
            violations.append(
                ContractViolation(
                    rule_id="EXTERNAL_DEPENDENCY_AFFECTS_UNKNOWN_TASK",
                    detail=external.id.value.hex,
                )
            )
    if value.horizon_end_utc <= value.now_utc:
        violations.append(
            ContractViolation(
                rule_id="HORIZON_MUST_END_AFTER_NOW",
                detail=str(value.horizon_end_utc),
            )
        )
    return tuple(violations)


def normalize_and_validate(value: PlannerInput) -> NormalizationResult:
    """Validate *value* and return either a valid result or typed failure."""
    violations = validate_contract(value)
    if violations:
        return InvalidPlannerInput(
            error_code="INVALID_INPUT",
            rule_ids=tuple(sorted({violation.rule_id for violation in violations})),
            prior_plan_snapshot=value.prior_plan_snapshot,
        )
    return ValidPlannerInput(value=value, input_hash=hash_canonical_input(value))
