"""Stable Rule IDs and decision evidence for explanations."""

from __future__ import annotations

from dataclasses import dataclass

RULE_DEPENDENCY_CYCLE = "DEPENDENCY_CYCLE"
RULE_INVALID_INPUT = "INVALID_INPUT"
RULE_SLOT_SINGLE_OWNER = "PLAN_SLOT_SINGLE_OWNER"
RULE_BASE_COVERAGE_BELOW_ONE = "BASE_COVERAGE_BELOW_ONE"
RULE_SAFETY_COVERAGE_BELOW_ONE = "SAFETY_COVERAGE_BELOW_ONE"
RULE_DATE_ONLY_UNKNOWN = "UNKNOWN_DATE_ONLY_DEADLINE"


@dataclass(frozen=True, slots=True)
class DecisionEvidence:
    """Explanation contract; LLM copy may only rephrase these fields."""

    selected_task_id: object | None
    priority_class: str | None
    rule_ids: tuple[str, ...]
    capacity_conflicts: int = 0


__all__ = ["DecisionEvidence", "RULE_DEPENDENCY_CYCLE"]
