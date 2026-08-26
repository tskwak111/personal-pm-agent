from __future__ import annotations

import pytest
from personal_pm_api.security.csrf import require_csrf_token
from personal_pm_api.security.rate_limit import RATE_LIMITS, RateLimiter


class _Request:
    def __init__(self, headers: dict[str, str], session_token: str = "sess-1") -> None:
        self.headers = headers
        self.session_token = session_token


def test_mutating_request_without_csrf_is_rejected() -> None:
    request = _Request({"X-CSRF-Token": ""})
    with pytest.raises(PermissionError):
        require_csrf_token(request, expected="tok-123")


def test_matching_csrf_passes() -> None:
    request = _Request({"X-CSRF-Token": "tok-123"})
    assert require_csrf_token(request, expected="tok-123") is True


def test_llm_rate_limit_is_separate_from_read_api() -> None:
    limiter = RateLimiter()
    actor_id = "user-1"
    llm_limit = RATE_LIMITS["llm"]
    for _ in range(llm_limit.max_requests):
        assert limiter.allow(actor_id, bucket=llm_limit) is True
    assert limiter.allow(actor_id, bucket=llm_limit) is False
    # Separate bucket: read API unaffected.
    assert limiter.allow(actor_id, bucket=RATE_LIMITS["read-api"]) is True


def test_upload_scan_rejects_executable_magic_bytes() -> None:
    from personal_pm_api.security.uploads import scan_upload

    exe_header = b"MZ" + b"\x90" * 64
    verdict = scan_upload(exe_header, declared_type="application/pdf")
    assert verdict.allowed is False


def test_upload_scan_allows_plain_text() -> None:
    from personal_pm_api.security.uploads import scan_upload

    verdict = scan_upload(b"hello world", declared_type="text/plain")
    assert verdict.allowed is True
