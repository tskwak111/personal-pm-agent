"""Intake structuring adapter: LLM output -> source-linked candidate facts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from personal_pm_worker.llm.schemas import SourceChunk, StructuredLLMRequest


@dataclass(frozen=True, slots=True)
class IntakeCandidate:
    """A structured LLM finding bound to its source location."""

    kind: str
    title: str
    due_date: str | None
    explicit_date: bool
    deterministic_parse: bool
    source_span: tuple[str, int, int] | None
    agreeing_sources: int
    has_conflict: bool
    model_confidence: float


DATE_HINTS = ("까지", "deadline", "due", "마감", "until", "by ")


def _looks_like_explicit_date(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in DATE_HINTS)


def build_intake_request(
    *,
    user_request: str,
    chunks: tuple[SourceChunk, ...],
    schema: type[Any],
    prompt_version: str = "intake-structuring-v1",
) -> StructuredLLMRequest[Any]:
    from personal_pm_worker.llm.schemas import StructuredLLMRequest as _Req

    return _Req(
        task_type="intake_structuring",
        prompt_version=prompt_version,
        schema=schema,
        verified_facts=(),
        user_request=user_request,
        untrusted_source_chunks=chunks,
    )


def to_candidate(
    value: Any,
    chunks: tuple[SourceChunk, ...],
    *,
    deterministic_parse: bool = False,
) -> IntakeCandidate:
    """Bind a validated LLM structure back to the chunk that produced it."""
    first_chunk = chunks[0] if chunks else None
    source_text = first_chunk.text if first_chunk else ""
    span: tuple[str, int, int] | None = None
    if first_chunk is not None:
        span = (
            "chunk",
            first_chunk.page_number if first_chunk.page_number is not None else 0,
            first_chunk.block_index,
        )
    due = getattr(value, "due_date", None)
    return IntakeCandidate(
        kind=getattr(value, "kind", None) or "REFERENCE_NOTE",
        title=str(getattr(value, "title", "") or ""),
        due_date=str(due) if due is not None else None,
        explicit_date=bool(due) and _looks_like_explicit_date(source_text),
        deterministic_parse=deterministic_parse,
        source_span=span,
        agreeing_sources=1,
        has_conflict=False,
        model_confidence=0.5,
    )


def detect_conflicts(candidates: list[IntakeCandidate]) -> list[IntakeCandidate]:
    """Flag candidates of the same kind+title with different dates."""
    by_key: dict[tuple[str, str], set[str]] = {}
    for cand in candidates:
        key = (cand.kind, cand.title.lower())
        by_key.setdefault(key, set()).add(cand.due_date or "")

    flagged: list[IntakeCandidate] = []
    for cand in candidates:
        key = (cand.kind, cand.title.lower())
        has_conflict = len(by_key[key]) > 1
        if has_conflict:
            flagged.append(
                IntakeCandidate(
                    kind=cand.kind,
                    title=cand.title,
                    due_date=cand.due_date,
                    explicit_date=cand.explicit_date,
                    deterministic_parse=cand.deterministic_parse,
                    source_span=cand.source_span,
                    agreeing_sources=cand.agreeing_sources,
                    has_conflict=True,
                    model_confidence=cand.model_confidence,
                )
            )
        else:
            flagged.append(cand)
    return flagged


__all__ = [
    "IntakeCandidate",
    "build_intake_request",
    "to_candidate",
    "detect_conflicts",
]
