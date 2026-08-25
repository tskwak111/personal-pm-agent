"""Deterministic intent classification: ambiguous language never mutates."""

from __future__ import annotations

from dataclasses import dataclass

QUESTION_MARKERS = ("뭐야", "무엇", "알려줘", "얼마나", "?")
REVIEW_MARKERS = (
    "어떨까",
    "하면 좋을까",
    "가능할까",
    "검토해",
    "미루는 게 나을까",
)
COMMAND_MARKERS = ("추가해", "미뤄", "변경해", "완료해", "시작해", "삭제해", "등록해")


@dataclass(frozen=True, slots=True)
class IntentResult:
    kind: str  # QUESTION | REVIEW_REQUEST | CHANGE_COMMAND | APPROVAL | AMBIGUOUS
    may_mutate: bool


def classify_intent(text: str) -> IntentResult:
    normalized = text.strip()
    if any(marker in normalized for marker in REVIEW_MARKERS):
        # Safe interpretation wins over command markers.
        return IntentResult(kind="REVIEW_REQUEST", may_mutate=False)
    if any(marker in normalized for marker in COMMAND_MARKERS):
        return IntentResult(kind="CHANGE_COMMAND", may_mutate=True)
    if any(marker in normalized for marker in QUESTION_MARKERS):
        return IntentResult(kind="QUESTION", may_mutate=False)
    return IntentResult(kind="AMBIGUOUS", may_mutate=False)


__all__ = ["IntentResult", "classify_intent"]
