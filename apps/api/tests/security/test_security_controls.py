from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient
from personal_pm_api.security.rate_limit import RATE_LIMITS, RateLimit, RateLimiter


def test_rate_limit_resets_after_window() -> None:
    limiter = RateLimiter()
    start = datetime(2026, 9, 1, tzinfo=UTC)
    limit = RateLimit(1, timedelta(minutes=10))

    assert limiter.allow("u", bucket_name="read-api", bucket=limit, now_utc=start)
    assert not limiter.allow(
        "u",
        bucket_name="read-api",
        bucket=limit,
        now_utc=start + timedelta(minutes=9),
    )
    assert limiter.allow(
        "u",
        bucket_name="read-api",
        bucket=limit,
        now_utc=start + timedelta(minutes=10),
    )


async def test_rate_limit_middleware_returns_429_before_endpoint() -> None:
    from personal_pm_api.main import create_app

    calls = 0
    start = datetime(2026, 9, 1, tzinfo=UTC)
    app = create_app(
        rate_limits={"read-api": RateLimit(1, timedelta(minutes=10))},
        rate_limit_clock=lambda: start,
    )

    @app.get("/api/v1/rate-test")
    async def endpoint() -> dict[str, bool]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        headers = {"Authorization": "Bearer test-session"}
        assert (await client.get("/api/v1/rate-test", headers=headers)).status_code == 200
        rejected = await client.get("/api/v1/rate-test", headers=headers)

    assert rejected.status_code == 429
    assert rejected.json()["code"] == "RATE_LIMITED"
    assert calls == 1


def test_llm_rate_limit_is_separate_from_read_api() -> None:
    limiter = RateLimiter()
    actor_id = "user-1"
    llm_limit = RATE_LIMITS["llm"]
    now = datetime(2026, 9, 1, tzinfo=UTC)
    for _ in range(llm_limit.max_requests):
        assert limiter.allow(actor_id, bucket_name="llm", bucket=llm_limit, now_utc=now) is True
    assert limiter.allow(actor_id, bucket_name="llm", bucket=llm_limit, now_utc=now) is False
    # Separate bucket: read API unaffected.
    assert (
        limiter.allow(
            actor_id,
            bucket_name="read-api",
            bucket=RATE_LIMITS["read-api"],
            now_utc=now,
        )
        is True
    )


def test_upload_scan_rejects_executable_magic_bytes() -> None:
    from personal_pm_api.security.uploads import scan_upload

    exe_header = b"MZ" + b"\x90" * 64
    verdict = scan_upload(exe_header, declared_type="application/pdf")
    assert verdict.allowed is False


def test_upload_scan_allows_plain_text() -> None:
    from personal_pm_api.security.uploads import scan_upload

    verdict = scan_upload(b"hello world", declared_type="text/plain")
    assert verdict.allowed is True
