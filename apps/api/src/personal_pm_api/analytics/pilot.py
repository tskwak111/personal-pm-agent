"""Controlled pilot outcome metrics (Stage D).

Active-user definition requires behavior, not logins. A system-caused
deadline delay can never be averaged away: it blocks release outright.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MANDATORY_OUTCOMES = frozenset({"OUT-001", "OUT-002", "OUT-005", "OUT-006"})


def is_active(*, days_used: int, task_actions: int, plan_views: int) -> bool:
    """Single source of truth for the behavioral active-user definition."""
    return days_used >= 3 and task_actions >= 5 and plan_views >= 2


def week_four_active(*, days_used: int, task_actions: int, plan_views: int) -> bool:
    return is_active(days_used=days_used, task_actions=task_actions, plan_views=plan_views)


@dataclass(frozen=True, slots=True)
class PilotOutcomeReport:
    release_eligible: bool
    system_caused_deadline_delays: int
    outcomes_passed: int


@dataclass(frozen=True, slots=True)
class PilotMetrics:
    mandatory_outcomes: frozenset[str] = field(default=MANDATORY_OUTCOMES)

    def week_four_active(self, *, days_used: int, task_actions: int, plan_views: int) -> bool:
        return is_active(days_used=days_used, task_actions=task_actions, plan_views=plan_views)

    async def build_outcome_report(
        self,
        *,
        system_caused_deadline_delays: int,
        outcomes: dict[str, bool],
        s0_incidents: int,
    ) -> PilotOutcomeReport:
        if s0_incidents or system_caused_deadline_delays:
            return PilotOutcomeReport(
                release_eligible=False,
                system_caused_deadline_delays=system_caused_deadline_delays,
                outcomes_passed=sum(1 for v in outcomes.values() if v),
            )
        mandatory_pass = all(outcomes.get(m, False) for m in self.mandatory_outcomes)
        return PilotOutcomeReport(
            release_eligible=mandatory_pass,
            system_caused_deadline_delays=0,
            outcomes_passed=sum(1 for v in outcomes.values() if v),
        )


__all__ = [
    "MANDATORY_OUTCOMES",
    "PilotMetrics",
    "PilotOutcomeReport",
    "is_active",
    "week_four_active",
]
