"""Briefing value types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BriefingContext:
    available_minutes: int
    fixed_events: tuple[tuple[str, int], ...]
    core_outcome: str
    must_do: tuple[tuple[str, int], ...]
    risk_cards: tuple[tuple[str, str], ...]
    decision_requests: tuple[str, ...]
    planner_rule_ids: tuple[str, ...]
    missed_minutes: int


@dataclass(frozen=True, slots=True)
class BriefingResult:
    rendered_text: str
    reason_rule_ids: tuple[str, ...]


__all__ = ["BriefingContext", "BriefingResult"]
