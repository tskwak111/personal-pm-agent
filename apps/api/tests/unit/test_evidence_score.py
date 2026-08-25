from __future__ import annotations

from personal_pm_api.inbox.evidence import CandidateFact, EvidenceScore, calculate_evidence_score


def _candidate(**overrides: object) -> CandidateFact:
    defaults: dict[str, object] = {
        "kind": "REFERENCE_NOTE",
        "model_confidence": 0.5,
        "explicit_date": False,
        "deterministic_parse": False,
        "source_span": None,
        "agreeing_sources": 1,
        "has_conflict": False,
    }
    merged = {**defaults, **overrides}
    return CandidateFact(**merged)  # type: ignore[arg-type]


def test_llm_self_confidence_cannot_produce_high_evidence_alone() -> None:
    candidate = _candidate(model_confidence=0.99)
    score = calculate_evidence_score(candidate)
    assert score.value < 0.65
    assert "MISSING_SOURCE_SPAN" in score.reasons


def test_explicit_date_parser_and_two_sources_raise_evidence() -> None:
    candidate = _candidate(
        explicit_date=True,
        deterministic_parse=True,
        agreeing_sources=2,
        source_span=("page", 3, 10),
    )
    score = calculate_evidence_score(candidate)
    assert score.value >= 0.90


def test_source_conflict_drops_score() -> None:
    candidate = _candidate(
        explicit_date=True,
        deterministic_parse=True,
        source_span=("page", 1, 2),
        has_conflict=True,
    )
    score = calculate_evidence_score(candidate)
    assert "SOURCE_CONFLICT" in score.reasons
    assert score.value <= 0.5


def test_score_is_clamped_to_unit_interval() -> None:
    low = calculate_evidence_score(_candidate(has_conflict=True))
    high = calculate_evidence_score(
        _candidate(
            explicit_date=True,
            deterministic_parse=True,
            source_span=("p", 1, 1),
            agreeing_sources=3,
        )
    )
    assert 0.0 <= low.value <= 1.0
    assert 0.0 <= high.value <= 1.0


def test_evidence_score_reasons_are_ordered() -> None:
    candidate = _candidate(model_confidence=0.99, has_conflict=True)
    score: EvidenceScore = calculate_evidence_score(candidate)
    assert score.reasons == tuple(sorted(score.reasons))
