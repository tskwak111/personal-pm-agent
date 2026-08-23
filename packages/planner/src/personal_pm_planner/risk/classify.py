"""Risk classification in the normative evaluation order.

Order per Planner Spec section 12.6: Definitive Critical, Unknown, capacity
Critical, High, Medium, Low. Each decision records stable Rule IDs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from personal_pm_planner.contracts.input import PlannerInput
from personal_pm_planner.domain.identifiers import MilestoneId
from personal_pm_planner.graph.build import GraphAnalysis, build_graph_analysis
from personal_pm_planner.risk.coverage import (
    MilestoneCoverage,
    free_slack_after_pass,
    milestone_coverages,
)
from personal_pm_planner.scheduling.passes import PlanningPasses


class RiskLevel(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    milestone_id: MilestoneId
    risk_level: str
    base_coverage: float
    safety_coverage: float
    slack_minutes: int | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RiskContext:
    value: PlannerInput
    analysis: GraphAnalysis

    @property
    def slot_minutes(self) -> int:
        return self.value.slot_minutes


def build_risk_context(value: PlannerInput) -> RiskContext:
    return RiskContext(value=value, analysis=build_graph_analysis(value))


def _medium_threshold(total_safety_minutes: int, slot_minutes: int) -> int:
    ten_percent = math.ceil((0.10 * total_safety_minutes) / slot_minutes) * slot_minutes
    return max(30, int(ten_percent))


def classify_milestone(
    coverage: MilestoneCoverage,
    slack_minutes: int | None,
    slot_minutes: int,
) -> tuple[RiskLevel, list[str]]:
    """Apply the normative classification order and return (level, rule ids)."""
    if coverage.has_cycle_member:
        return RiskLevel.CRITICAL, ["DEPENDENCY_CYCLE_BLOCKS_REQUIRED_PATH"]
    if coverage.date_only:
        # A date-only deadline has no verified time; it stays Unknown and can
        # never reach Low until the user confirms a time.
        return RiskLevel.UNKNOWN, ["UNKNOWN_DATE_ONLY_DEADLINE"]
    if coverage.deadline_limit is None:
        return RiskLevel.UNKNOWN, ["UNKNOWN_MISSING_DEADLINE"]
    if coverage.base_coverage < 1.0:
        return RiskLevel.CRITICAL, ["BASE_COVERAGE_BELOW_ONE"]
    if coverage.safety_coverage < 1.0:
        return RiskLevel.HIGH, ["SAFETY_COVERAGE_BELOW_ONE"]
    if coverage.buffers_allocated_minutes < coverage.buffer_required_minutes:
        return RiskLevel.HIGH, ["MANDATORY_BUFFER_UNALLOCATED"]

    threshold = _medium_threshold(
        coverage.safety_required_minutes + coverage.buffer_required_minutes,
        slot_minutes,
    )
    effective_slack = slack_minutes if slack_minutes is not None else 0
    if effective_slack < threshold:
        return RiskLevel.MEDIUM, ["SLACK_BELOW_THRESHOLD"]
    return RiskLevel.LOW, []


def calculate_risks(
    passes: PlanningPasses,
    context: RiskContext,
) -> dict[MilestoneId, RiskAssessment]:
    assessments: dict[MilestoneId, RiskAssessment] = {}
    for coverage in milestone_coverages(
        value=context.value, passes=passes, analysis=context.analysis
    ):
        provisional_level, provisional_reasons = classify_milestone(
            coverage, None, context.slot_minutes
        )
        slack: int | None = None
        if provisional_level in (RiskLevel.MEDIUM, RiskLevel.LOW):
            slack = free_slack_after_pass(context.value, passes, coverage.deadline_limit)
            level, reasons = classify_milestone(coverage, slack, context.slot_minutes)
        else:
            level, reasons = provisional_level, provisional_reasons
        assessments[coverage.milestone_id] = RiskAssessment(
            milestone_id=coverage.milestone_id,
            risk_level=level.value,
            base_coverage=round(coverage.base_coverage, 4),
            safety_coverage=round(coverage.safety_coverage, 4),
            slack_minutes=slack,
            reasons=tuple(reasons),
        )
    return assessments


__all__ = [
    "RiskAssessment",
    "RiskContext",
    "RiskLevel",
    "build_risk_context",
    "calculate_risks",
]
