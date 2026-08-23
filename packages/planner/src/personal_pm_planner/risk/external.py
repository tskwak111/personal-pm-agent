"""External dependency risk from latest-safe-handoff timing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from personal_pm_planner.contracts.input import PlannerInput
from personal_pm_planner.graph.build import GraphAnalysis
from personal_pm_planner.risk.classify import RiskLevel


@dataclass(frozen=True, slots=True)
class ExternalRiskAssessment:
    external_dependency_id: object
    risk_level: str
    latest_safe_handoff_at: datetime | None
    reasons: tuple[str, ...]


def assess_external_dependencies(
    value: PlannerInput,
    analysis: GraphAnalysis,
) -> list[ExternalRiskAssessment]:
    assessments: list[ExternalRiskAssessment] = []
    for external in value.external_dependencies:
        analysis_entry = next(
            (
                entry
                for entry in analysis.external_dependencies
                if entry.external_dependency_id == external.id
            ),
            None,
        )
        handoff = analysis_entry.latest_safe_handoff_at if analysis_entry else None
        delivery = external.expected_delivery_at

        if handoff is None or delivery is None:
            assessments.append(
                ExternalRiskAssessment(
                    external_dependency_id=external.id,
                    risk_level=RiskLevel.UNKNOWN.value,
                    latest_safe_handoff_at=handoff,
                    reasons=("EXTERNAL_TIMING_UNKNOWN",),
                )
            )
            continue

        margin = handoff - delivery
        if value.now_utc > handoff and not external.fallback_available:
            level = RiskLevel.CRITICAL
            reason_ids: tuple[str, ...] = ("HANDOFF_PASSED_WITHOUT_FALLBACK",)
        elif margin.total_seconds() < 0:
            level = RiskLevel.HIGH
            reason_ids = ("EXPECTED_DELIVERY_AFTER_LATEST_SAFE_HANDOFF",)
        elif margin <= _timedelta_minutes(external.uncertainty_buffer_minutes):
            level = RiskLevel.MEDIUM
            reason_ids = ("DELIVERY_MARGIN_WITHIN_UNCERTAINTY_BUFFER",)
        else:
            level = RiskLevel.LOW
            reason_ids = ()

        assessments.append(
            ExternalRiskAssessment(
                external_dependency_id=external.id,
                risk_level=level.value,
                latest_safe_handoff_at=handoff,
                reasons=reason_ids,
            )
        )
    return assessments


def _timedelta_minutes(minutes: int) -> timedelta:
    return timedelta(minutes=minutes)
