"""Per-actor bucketed rate limits (frozen product policy)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class RateLimit:
    max_requests: int
    window: timedelta


RATE_LIMITS = {
    "auth": RateLimit(10, timedelta(minutes=10)),
    "upload": RateLimit(20, timedelta(hours=1)),
    "llm": RateLimit(100, timedelta(days=1)),
    "external-write": RateLimit(30, timedelta(hours=1)),
    "read-api": RateLimit(600, timedelta(minutes=10)),
}


class RateLimiter:
    """Fixed-window counter keyed by (actor, bucket name)."""

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], int] = {}

    def allow(self, actor_id: str, *, bucket: RateLimit) -> bool:
        key = (actor_id, id(bucket))
        current = self._counts.get(key, 0)
        if current >= bucket.max_requests:
            return False
        self._counts[key] = current + 1
        return True


__all__ = ["RATE_LIMITS", "RateLimit", "RateLimiter"]
