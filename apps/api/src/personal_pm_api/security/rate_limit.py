"""Per-actor bucketed rate limits (frozen product policy)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError


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
        self._counters: dict[tuple[str, str], tuple[datetime, int]] = {}
        self._lock = Lock()

    async def allow(
        self,
        actor_id: str,
        *,
        bucket_name: str,
        bucket: RateLimit,
        now_utc: datetime,
    ) -> bool:
        if now_utc.tzinfo is None or now_utc.utcoffset() is None:
            raise ValueError("rate-limit clock must be timezone-aware")
        key = (actor_id, bucket_name)
        with self._lock:
            window_start, count = self._counters.get(key, (now_utc, 0))
            if now_utc - window_start >= bucket.window:
                window_start, count = now_utc, 0
            if count >= bucket.max_requests:
                return False
            self._counters[key] = (window_start, count + 1)
            return True


class RateLimiterPort(Protocol):
    async def allow(
        self,
        actor_id: str,
        *,
        bucket_name: str,
        bucket: RateLimit,
        now_utc: datetime,
    ) -> bool: ...


class RedisRateLimiter:
    """Atomic fixed-window counters shared by all production replicas."""

    _SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[1]) end
return count
"""

    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_url(cls, url: str) -> RedisRateLimiter:
        return cls(Redis.from_url(url, decode_responses=True))

    async def allow(
        self,
        actor_id: str,
        *,
        bucket_name: str,
        bucket: RateLimit,
        now_utc: datetime,
    ) -> bool:
        if now_utc.tzinfo is None or now_utc.utcoffset() is None:
            raise ValueError("rate-limit clock must be timezone-aware")
        key = f"personal-pm:rate:{bucket_name}:{actor_id}"
        window_ms = max(1, int(bucket.window.total_seconds() * 1000))
        try:
            count = await self._client.eval(self._SCRIPT, 1, key, window_ms)
        except (OSError, RedisError):
            return False
        return int(count) <= bucket.max_requests


__all__ = [
    "RATE_LIMITS",
    "RateLimit",
    "RateLimiter",
    "RateLimiterPort",
    "RedisRateLimiter",
]
