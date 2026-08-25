from __future__ import annotations

from personal_pm_api.inbox.evidence import CandidateFact
from personal_pm_api.inbox.registration_policy import decide_registration


def _candidate(**overrides: object) -> CandidateFact:
    defaults: dict[str, object] = {
        "kind": "REFERENCE_NOTE",
        "model_confidence": 0.5,
        "explicit_date": True,
        "deterministic_parse": True,
        "source_span": ("chunk", 1, 0),
        "agreeing_sources": 2,
        "has_conflict": False,
    }
    merged = {**defaults, **overrides}
    return CandidateFact(**merged)  # type: ignore[arg-type]


class _PolicyCandidate:
    """Wraps a CandidateFact with policy-relevant enrichment."""

    def __init__(
        self,
        fact: CandidateFact,
        *,
        time_known: bool = True,
        expected_harm: str = "LOW",
        evidence_score: float | None = None,
    ) -> None:
        self.fact = fact
        self.kind = fact.kind
        self.has_conflict = fact.has_conflict
        self.time_known = time_known
        self.expected_harm = expected_harm
        from personal_pm_api.inbox.evidence import calculate_evidence_score

        self.evidence_score = (
            evidence_score if evidence_score is not None else calculate_evidence_score(fact).value
        )


def test_hard_deadline_with_unknown_time_requires_confirmation() -> None:
    candidate = _PolicyCandidate(
        _candidate(kind="HARD_DEADLINE"), time_known=False, expected_harm="HIGH"
    )
    decision = decide_registration(candidate)
    assert decision.action == "NEEDS_CONFIRMATION"
    assert decision.reason == "TIME_UNKNOWN"


def test_low_harm_note_with_high_evidence_can_auto_register() -> None:
    candidate = _PolicyCandidate(
        _candidate(kind="REFERENCE_NOTE", explicit_date=False, deterministic_parse=False),
        expected_harm="LOW",
    )
    decision = decide_registration(candidate, evidence_score=0.95)
    assert decision.action == "AUTO_REGISTER"


def test_source_conflict_always_requires_confirmation() -> None:
    candidate = _PolicyCandidate(_candidate(has_conflict=True))
    decision = decide_registration(candidate, evidence_score=0.99)
    assert decision.action == "NEEDS_CONFIRMATION"
    assert decision.reason == "SOURCE_CONFLICT"


def test_high_expected_harm_requires_confirmation() -> None:
    candidate = _PolicyCandidate(_candidate(kind="FIXED_EVENT"), expected_harm="HIGH")
    decision = decide_registration(candidate, evidence_score=0.99)
    assert decision.action == "NEEDS_CONFIRMATION"


def test_medium_evidence_becomes_temporary() -> None:
    candidate = _PolicyCandidate(_candidate(), expected_harm="LOW")
    decision = decide_registration(candidate, evidence_score=0.70)
    assert decision.action == "TEMPORARY"


def test_low_evidence_is_held() -> None:
    candidate = _PolicyCandidate(
        _candidate(explicit_date=False, deterministic_parse=False), expected_harm="LOW"
    )
    decision = decide_registration(candidate, evidence_score=0.30)
    assert decision.action == "HOLD"
