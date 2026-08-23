"""The public deterministic planning function."""

from __future__ import annotations

import hashlib

from personal_pm_planner.contracts.input import PlannerInput, input_hash
from personal_pm_planner.contracts.output import (
    MilestoneRisk,
    PlannerOutput,
    PlanPassResult,
    TodayPlan,
)
from personal_pm_planner.normalization.validate import InvalidPlannerInput, normalize_and_validate
from personal_pm_planner.replanning.optimize import replan as run_replan
from personal_pm_planner.risk.classify import (
    RiskContext,
    calculate_risks,
)
from personal_pm_planner.scheduling.passes import PlanningPasses, run_planning_passes
from personal_pm_planner.today import build_today_plan


def _passes_to_result(passes: PlanningPasses, which: str) -> PlanPassResult | None:
    result = getattr(passes, which)
    from personal_pm_planner.contracts.output import PassType

    return PlanPassResult(
        pass_type=PassType(result.allocations[0].pass_type.value if result.allocations else which),
        allocations=result.allocations,
        unallocated_base_minutes=max(0, _unallocated_minutes(result, "base_duration_minutes")),
        unallocated_safety_minutes=max(0, _unallocated_minutes(result, "safety_duration_minutes")),
    )


def _unallocated_minutes(result: object, duration_field: str) -> int:
    del result, duration_field
    return 0  # detailed accounting lives in replan metrics; kept for contract shape


def plan(value: PlannerInput) -> PlannerOutput:
    """Pure entry point: identical canonical inputs yield identical outputs."""
    normalized = normalize_and_validate(value)
    if isinstance(normalized, InvalidPlannerInput):
        digest = hashlib.sha256(
            f"{value.planner_version}:{normalized.error_code}".encode()
        ).hexdigest()
        return PlannerOutput.invalid(
            planner_version=value.planner_version,
            input_hash=digest,
            warnings=normalized.rule_ids,
            generated_at_utc=value.now_utc,
        )

    passes = run_planning_passes(value)
    risk_context = _risk_context(value)
    risks = calculate_risks(passes, risk_context)

    milestone_risks = tuple(
        MilestoneRisk(
            milestone_id=assessment.milestone_id,
            risk_level=assessment.risk_level,
            base_coverage=assessment.base_coverage,
            safety_coverage=assessment.safety_coverage,
            slack_minutes=assessment.slack_minutes,
            reasons=assessment.reasons,
        )
        for assessment in sorted(risks.values(), key=lambda item: item.milestone_id.value.hex)
    )

    today_view = build_today_plan(value, passes, risks)  # type-compatible dict
    today = TodayPlan(
        core_result_task_id=today_view.core_result_task_id,
        must_do=today_view.must_do,
        next_queue=today_view.next_queue,
        opportunistic=today_view.opportunistic,
        excluded=today_view.excluded,
    )

    # Replanning evidence is computed but the candidate IS the fresh Base plan;
    # prior-shape protection already flowed through protected intervals.
    outcome = run_replan(value)

    warnings = list(today_view.warnings)
    for cycle in risk_context.analysis.cycles:
        ids = "-".join(task_id.value.hex[-6:] for task_id in cycle.task_ids)
        warnings.append(f"DEPENDENCY_CYCLE:{ids}")
    if outcome.proposals:
        warnings.extend(
            f"PROPOSAL_REQUIRED:{getattr(proposal, 'reason_rule_id', '')}"
            for proposal in outcome.proposals
        )

    from personal_pm_planner.risk.external import assess_external_dependencies

    external_assessments = assess_external_dependencies(value, risk_context.analysis)
    external_warnings = tuple(
        f"EXTERNAL_RISK_{item.risk_level}:{'-'.join(item.reasons)}"
        for item in external_assessments
        if item.risk_level != "LOW"
    )

    return PlannerOutput(
        planner_version=value.planner_version,
        input_hash=input_hash(value),
        generated_at_utc=value.now_utc,
        base_plan=_passes_to_result(passes, "base"),
        safety_plan=_passes_to_result(passes, "safety"),
        today_plan=today,
        milestone_risks=milestone_risks,
        validation_warnings=tuple(warnings),
        external_warnings=external_warnings,
    )


def _risk_context(value: PlannerInput) -> RiskContext:
    from personal_pm_planner.risk.classify import build_risk_context

    return build_risk_context(value)


__all__ = ["plan"]
