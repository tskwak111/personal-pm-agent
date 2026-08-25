"""Expected-harm auto-registration policy.

Automation is minimized: conflicts, unknown times on hard deadlines/events,
and high expected harm always require user confirmation. Only low-harm,
high-evidence candidates may auto-register.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

HARD_KINDS = frozenset({"HARD_DEADLINE", "FIXED_EVENT"})
AUTO_EVIDENCE_THRESHOLD = 0.90
TEMPORARY_EVIDENCE_THRESHOLD = 0.65


@dataclass(frozen=True, slots=True)
class RegistrationDecision:
    action: str
    reason: str


def decide_registration(
    candidate: Any, *, evidence_score: float | None = None
) -> RegistrationDecision:
    """Decide Auto/Temporary/Needs Confirmation/Hold for one candidate."""
    score = (
        evidence_score if evidence_score is not None else float(candidate.evidence_score)
    )
    kind = str(candidate.kind)
    has_conflict = bool(candidate.has_conflict)
    time_known = getattr(candidate, "time_known", True)
    expected_harm = str(getattr(candidate, "expected_harm", "LOW")).upper()

    if has_conflict:
        return RegistrationDecision("NEEDS_CONFIRMATION", "SOURCE_CONFLICT")
    if kind in HARD_KINDS and not time_known:
        return RegistrationDecision("NEEDS_CONFIRMATION", "TIME_UNKNOWN")
    if expected_harm == "HIGH":
        return RegistrationDecision("NEEDS_CONFIRMATION", "HIGH_EXPECTED_HARM")
    if score >= AUTO_EVIDENCE_THRESHOLD and expected_harm == "LOW":
        return RegistrationDecision("AUTO_REGISTER", "HIGH_EVIDENCE_LOW_HARM")
    if score >= TEMPORARY_EVIDENCE_THRESHOLD:
        return RegistrationDecision("TEMPORARY", "MEDIUM_EVIDENCE")
    return RegistrationDecision("HOLD", "LOW_EVIDENCE")


__all__ = ["RegistrationDecision", "decide_registration"]
