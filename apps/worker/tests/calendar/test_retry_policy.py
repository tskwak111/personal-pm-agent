from __future__ import annotations

from personal_pm_worker.calendar.retry import classify_failure


def test_oauth_expiration_never_retries_as_transient() -> None:
    decision = classify_failure(status_code=401, provider_code="invalid_grant", attempt=1)
    assert decision.action == "NEEDS_REAUTHORIZATION"
    assert decision.delay_seconds is None


def test_rate_limit_uses_bounded_backoff() -> None:
    decision = classify_failure(status_code=429, provider_code=None, attempt=3)
    assert decision.action == "RETRY"
    assert 1 <= (decision.delay_seconds or 0) <= 900


def test_server_errors_retry_with_backoff() -> None:
    decision = classify_failure(status_code=503, provider_code=None, attempt=1)
    assert decision.action == "RETRY"
    assert (decision.delay_seconds or 0) <= 900


def test_transient_attempts_exhaust_to_dead_letter() -> None:
    decision = classify_failure(status_code=429, provider_code=None, attempt=5)
    assert decision.action == "DEAD_LETTER"
    assert decision.delay_seconds is None


def test_client_error_is_dead_letter_immediately() -> None:
    decision = classify_failure(status_code=400, provider_code="invalid_request", attempt=1)
    assert decision.action == "DEAD_LETTER"


def test_timeout_is_treated_as_transient() -> None:
    decision = classify_failure(None, None, attempt=2, timeout=True)
    assert decision.action == "RETRY"


def test_forbidden_requires_reauthorization() -> None:
    decision = classify_failure(status_code=403, provider_code=None, attempt=1)
    assert decision.action == "NEEDS_REAUTHORIZATION"
