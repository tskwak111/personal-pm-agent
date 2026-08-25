"""Deterministic retry classification for provider failures.

OAuth expiry NEVER retries as transient: it requires reauthorization.
Transient errors get bounded exponential backoff; everything else is a
dead letter.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_BACKOFF_SECONDS = 900
MAX_TRANSIENT_ATTEMPTS = 5


@dataclass(frozen=True, slots=True)
class RetryDecision:
    action: str  # RETRY | NEEDS_REAUTHORIZATION | DEAD_LETTER
    delay_seconds: int | None


def deterministic_jitter(attempt: int) -> int:
    """Attempt-derived jitter in [0, attempt] seconds (no wall-clock entropy)."""
    return attempt % 4


def classify_failure(
    status_code: int | None,
    provider_code: str | None,
    attempt: int,
    *,
    timeout: bool = False,
) -> RetryDecision:
    if provider_code == "invalid_grant" or status_code == 401 or status_code == 403:
        return RetryDecision("NEEDS_REAUTHORIZATION", None)
    if (
        timeout
        or status_code == 408
        or status_code == 429
        or (status_code is not None and status_code >= 500)
    ):
        if attempt >= MAX_TRANSIENT_ATTEMPTS:
            return RetryDecision("DEAD_LETTER", None)
        delay = min(MAX_BACKOFF_SECONDS, 2**attempt + deterministic_jitter(attempt))
        return RetryDecision("RETRY", delay)
    return RetryDecision("DEAD_LETTER", None)


__all__ = ["RetryDecision", "classify_failure", "deterministic_jitter"]
