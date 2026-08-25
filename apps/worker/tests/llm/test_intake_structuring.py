from __future__ import annotations

import asyncio
from dataclasses import dataclass

from personal_pm_worker.llm.adapters.intake import (
    IntakeCandidate,
    build_intake_request,
    detect_conflicts,
    to_candidate,
)
from personal_pm_worker.llm.fake import FakeLLMGateway
from personal_pm_worker.llm.schemas import SourceChunk

CHUNKS = (SourceChunk(text="CS101 report due 2026-09-01", page_number=2, block_index=1),)


@dataclass
class Extracted:
    title: str
    due_date: str | None = None


def test_candidate_binds_source_span_from_chunk() -> None:
    request = build_intake_request(user_request="extract", chunks=CHUNKS, schema=Extracted)
    gateway = FakeLLMGateway()

    gateway.enqueue_raw('{"title": "CS101 report", "due_date": "2026-09-01"}')
    structured = asyncio.run(gateway.generate_structured(request))
    candidate = to_candidate(structured.value, CHUNKS)
    assert candidate.source_span == ("chunk", 2, 1)
    assert candidate.due_date == "2026-09-01"
    assert candidate.title == "CS101 report"
    assert candidate.explicit_date is True


def test_missing_span_flags_low_evidence_reason() -> None:
    from personal_pm_api.inbox.evidence import calculate_evidence_score

    candidate = IntakeCandidate(
        kind="REFERENCE_NOTE",
        title="x",
        due_date=None,
        explicit_date=False,
        deterministic_parse=False,
        source_span=None,
        agreeing_sources=1,
        has_conflict=False,
        model_confidence=0.9,
    )
    score = calculate_evidence_score(candidate)
    assert "MISSING_SOURCE_SPAN" in score.reasons
    assert score.value < 0.65


def test_detect_conflicts_flags_differing_dates() -> None:
    base = dict(
        kind="HARD_DEADLINE",
        title="Report",
        explicit_date=True,
        deterministic_parse=True,
        source_span=("chunk", 1, 0),
        agreeing_sources=1,
        model_confidence=0.5,
    )
    a = IntakeCandidate(due_date="2026-09-01", has_conflict=False, **base)  # type: ignore[arg-type]
    b = IntakeCandidate(due_date="2026-09-15", has_conflict=False, **base)  # type: ignore[arg-type]
    flagged = detect_conflicts([a, b])
    assert all(c.has_conflict for c in flagged)


def test_no_conflict_when_dates_agree() -> None:
    base = dict(
        kind="HARD_DEADLINE",
        title="Report",
        due_date="2026-09-01",
        explicit_date=True,
        deterministic_parse=True,
        source_span=("chunk", 1, 0),
        agreeing_sources=2,
        model_confidence=0.5,
        has_conflict=False,
    )
    a = IntakeCandidate(**base)  # type: ignore[arg-type]
    b = IntakeCandidate(**base)  # type: ignore[arg-type]
    flagged = detect_conflicts([a, b])
    assert all(not c.has_conflict for c in flagged)
