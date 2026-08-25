"""Deterministic evidence scoring for extracted candidate facts.

LLM self-confidence NEVER contributes to the score: only source-grounded
signals (explicit dates, deterministic parses, source spans, agreeing
sources) raise it, and conflicts lower it.
"""

from __future__ import annotations

from dataclasses import dataclass

SourceSpan = tuple[str, int, int]


@dataclass(frozen=True, slots=True)
class CandidateFact:
    kind: str
    model_confidence: float
    explicit_date: bool
    deterministic_parse: bool
    source_span: SourceSpan | None
    agreeing_sources: int
    has_conflict: bool


@dataclass(frozen=True, slots=True)
class EvidenceScore:
    value: float
    reasons: tuple[str, ...]


def calculate_evidence_score(candidate: CandidateFact) -> EvidenceScore:
    points = 0.0
    reasons: list[str] = []
    if candidate.explicit_date:
        points += 0.25
    if candidate.deterministic_parse:
        points += 0.25
    if candidate.source_span is not None:
        points += 0.20
    else:
        reasons.append("MISSING_SOURCE_SPAN")
    if candidate.agreeing_sources >= 2:
        points += 0.20
    if candidate.has_conflict:
        points -= 0.50
        reasons.append("SOURCE_CONFLICT")
    return EvidenceScore(value=max(0.0, min(1.0, round(points, 6))), reasons=tuple(sorted(reasons)))


__all__ = ["CandidateFact", "EvidenceScore", "calculate_evidence_score"]
