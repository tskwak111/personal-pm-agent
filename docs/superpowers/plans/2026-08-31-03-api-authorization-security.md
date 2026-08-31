# API Authorization and Security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce authorization, rate, upload, OAuth, readiness, and logging controls on live API paths.

**Architecture:** FastAPI dependencies and middleware enforce trust boundaries before domain services run. Existing approval and upload services remain the single behavior owners; unavailable OAuth/provider infrastructure fails closed.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async, cryptography, pytest/httpx

**Spec:** `docs/superpowers/specs/2026-08-31-aaa-production-readiness-design.md`

## Global Constraints

- Bearer-token requests remain the only authentication mode; browsers do not receive an ambient auth cookie.
- Ownership, proposal version, target version, and proposal payload hash are validated before execution.
- OAuth tokens are encrypted before persistence and never logged.
- Untrusted files cannot enqueue tools or external actions.
- Readiness is false when required database access fails.

---

### Task 1: Add resettable live rate limits and remove dead CSRF claims

**Files:**
- Modify: `apps/api/src/personal_pm_api/security/rate_limit.py`
- Modify: `apps/api/src/personal_pm_api/main.py`
- Modify: `apps/api/src/personal_pm_api/security/csrf.py`
- Test: `apps/api/tests/security/test_security_controls.py`

**Interfaces:**
- Produces: `RateLimiter.allow(actor_id, bucket_name, now_utc) -> bool`
- Produces: 429 with `RATE_LIMITED` for exhausted auth/upload/external-write/read buckets

- [ ] **Step 1: Write clock and middleware regressions**

```python
def test_rate_limit_resets_after_window() -> None:
    limiter = RateLimiter()
    start = datetime(2026, 9, 1, tzinfo=UTC)
    limit = RateLimit(1, timedelta(minutes=10))
    assert limiter.allow("u", bucket=limit, now_utc=start)
    assert not limiter.allow("u", bucket=limit, now_utc=start + timedelta(minutes=9))
    assert limiter.allow("u", bucket=limit, now_utc=start + timedelta(minutes=10))
```

Add an ASGI test that exhausts a configured test limit and receives 429 before the endpoint runs.

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/security/test_security_controls.py -q`

- [ ] **Step 3: Store window start with count**

```python
self._counters: dict[tuple[str, int, timedelta], tuple[datetime, int]] = {}
window_start, count = self._counters.get(key, (now_utc, 0))
if now_utc - window_start >= bucket.window:
    window_start, count = now_utc, 0
```

Wire middleware using actor/session identity when available and client address only for unauthenticated auth routes. Inject a clock in tests.

- [ ] **Step 4: Make CSRF status truthful**

Delete the unused `require_csrf_token` helper and its fake unit tests. Add a contract test proving authentication rejects cookie-only requests and requires `Authorization: Bearer`; document CSRF as not applicable until ambient cookie auth is introduced.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest apps/api/tests/security/test_security_controls.py apps/api/tests/integration/test_identity_and_ownership.py -q
git add apps/api/src/personal_pm_api/security apps/api/src/personal_pm_api/main.py apps/api/tests/security/test_security_controls.py
git commit -m "feat(security): enforce resettable API rate limits"
```

### Task 2: Enforce upload scanning before persistence and extraction

**Files:**
- Modify: `apps/api/src/personal_pm_api/inbox/router.py`
- Modify: `apps/api/src/personal_pm_api/security/uploads.py`
- Test: `apps/api/tests/integration/test_source_upload.py`
- Test: `apps/worker/tests/security/test_prompt_injection_boundary.py`

**Interfaces:**
- Consumes: raw bytes and declared media type
- Produces: 415 `UPLOAD_TYPE_MISMATCH` or 422 `UPLOAD_REJECTED` before `SourceArtifactModel` creation

- [ ] **Step 1: Write the failing endpoint test**

```python
response = await client.post(
    "/api/v1/inbox/sources",
    files={"file": ("notice.pdf", b"MZ" + b"x" * 64, "application/pdf")},
)
assert response.status_code == 422
assert await source_count(factory) == 0
assert await outbox_count(factory) == 0
```

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/integration/test_source_upload.py -q`

- [ ] **Step 3: Validate supported magic and size**

Use a fixed allowlist for PDF, PNG, JPEG, and UTF-8 text. Reject executable/polyglot prefixes, NUL-bearing text, invalid UTF-8 text, and bytes over the configured maximum. Run `scan_upload` before any insert or extraction enqueue.

- [ ] **Step 4: Verify trust-boundary regressions**

```bash
uv run pytest apps/api/tests/integration/test_source_upload.py apps/worker/tests/files/test_extraction_pipeline.py apps/worker/tests/security/test_prompt_injection_boundary.py -q
```

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/personal_pm_api/inbox/router.py apps/api/src/personal_pm_api/security/uploads.py apps/api/tests/integration/test_source_upload.py apps/worker/tests/security/test_prompt_injection_boundary.py
git commit -m "feat(files): reject unsafe uploads before persistence"
```

### Task 3: Route proposal decisions through ApprovalService

**Files:**
- Modify: `apps/api/src/personal_pm_api/approvals/router.py`
- Modify: `apps/api/src/personal_pm_api/approvals/service.py`
- Modify: `apps/api/src/personal_pm_api/audit/repository.py`
- Test: `apps/api/tests/integration/test_approval_service.py`
- Create: `apps/api/tests/integration/test_approval_router.py`

**Interfaces:**
- Consumes: `decision: Literal["approve","reject"]`, `expected_version: int`, actor
- Produces: service outcome mapped to 200/404/409/422; audit event in the same transaction

- [ ] **Step 1: Write router regressions**

```python
response = await client.post(
    f"/api/v1/proposals/{proposal_id}/approve",
    json={"decision": "approve", "expected_version": proposal_version},
)
assert response.status_code == 200
assert response.json()["status"] == "EXECUTED"
```

Add wrong workspace → 404, stale proposal → 409, changed target → 409/SUPERSEDED, unknown decision → 422, and one matching audit row.

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/integration/test_approval_router.py -q`

- [ ] **Step 3: Use the existing service**

Change the request schema to:

```python
class ApproveProposalRequest(BaseModel):
    decision: Literal["approve", "reject"]
    expected_version: int = Field(ge=1)
```

Create `ApprovalService(database_session_factory())` through a FastAPI dependency. Remove direct `ProposalModel.status` mutation from the router.

- [ ] **Step 4: Verify payload integrity and audit**

Before applying values, recompute the canonical JSON SHA-256 of `targets_json` and compare it with `payload_hash`. Emit an audit event before commit; both mutation and audit roll back together.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest apps/api/tests/integration/test_approval_service.py apps/api/tests/integration/test_approval_router.py apps/api/tests/integration/test_unit_of_work.py -q
git add apps/api/src/personal_pm_api/approvals apps/api/src/personal_pm_api/audit apps/api/tests/integration/test_approval_service.py apps/api/tests/integration/test_approval_router.py
git commit -m "fix(approvals): execute version-bound decisions"
```

### Task 4: Make OAuth connection state verifiable

**Files:**
- Modify: `apps/api/src/personal_pm_api/calendar/oauth.py`
- Modify: `apps/api/src/personal_pm_api/calendar/router.py`
- Create: `apps/api/src/personal_pm_api/calendar/connections.py`
- Create: `apps/api/migrations/versions/0011_calendar_connections.py`
- Test: `apps/api/tests/integration/test_calendar_oauth.py`

**Interfaces:**
- Produces: `exchange_authorization_code(code, redirect_uri, settings) -> TokenResponse`
- Produces: encrypted `CalendarConnectionModel` only after provider response validation
- Produces: 400 missing code/state, 503 unconfigured provider, 502 rejected exchange

- [ ] **Step 1: Write missing-code and unconfigured-provider tests**

```python
response = await client.get(f"/api/v1/calendar/oauth/callback?state={state}")
assert response.status_code == 400
assert response.json()["code"] == "OAUTH_CODE_MISSING"

response = await client.get(f"/api/v1/calendar/oauth/callback?state={state}&code=x")
assert response.status_code == 503
assert response.json()["code"] == "OAUTH_PROVIDER_NOT_CONFIGURED"
```

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/integration/test_calendar_oauth.py -q`

- [ ] **Step 3: Bind state to workspace, mode, verifier, and expiry**

Store a dataclass value instead of a workspace string. Consume only once and reject expired state. Generate PKCE `code_verifier`/`code_challenge`; use `urllib.parse.urlencode` instead of manual query concatenation.

- [ ] **Step 4: Exchange and persist only verified tokens**

Use `httpx.AsyncClient` in one concrete function. Require access token, refresh token, expiry, and granted scopes; encrypt tokens with the existing `TokenVault`. Set connection status `CONNECTED` only after commit. Provider secrets come from `ApiSettings`.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest apps/api/tests/integration/test_calendar_oauth.py -q
git add apps/api/src/personal_pm_api/calendar apps/api/migrations/versions/0011_calendar_connections.py apps/api/tests/integration/test_calendar_oauth.py
git commit -m "feat(calendar): verify OAuth before connection"
```

### Task 5: Make readiness and logs live

**Files:**
- Modify: `apps/api/src/personal_pm_api/main.py`
- Modify: `apps/api/src/personal_pm_api/telemetry/logging.py`
- Modify: `apps/api/src/personal_pm_api/telemetry/tracing.py`
- Test: `apps/api/tests/test_health.py`
- Test: `apps/api/tests/unit/test_sensitive_log_filter.py`

**Interfaces:**
- Produces: `/health/ready` executes `SELECT 1`
- Produces: request correlation ID response header and sanitized structured request result log

- [ ] **Step 1: Write failing dependency-health tests**

```python
async def test_ready_returns_503_when_database_fails(monkeypatch) -> None:
    monkeypatch.setattr("personal_pm_api.main.check_database", AsyncMock(side_effect=OSError()))
    response = await client.get("/health/ready")
    assert response.status_code == 503
```

Add a request test containing `Authorization` and `workspace_id`; assert captured logs exclude the token and contain only `workspace_hash`.

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/test_health.py apps/api/tests/unit/test_sensitive_log_filter.py -q`

- [ ] **Step 3: Implement one request middleware**

Read or generate a valid correlation ID, attach it to response headers, and log method/path/status/duration with the sanitizer. Add `authorization`, `cookie`, `code`, and `file_content` to sensitive keys. Do not log bodies.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest apps/api/tests/test_health.py apps/api/tests/unit/test_sensitive_log_filter.py apps/api/tests/unit/test_telemetry_events.py -q
uv run mypy apps/api/src
git add apps/api/src/personal_pm_api/main.py apps/api/src/personal_pm_api/telemetry apps/api/tests/test_health.py apps/api/tests/unit/test_sensitive_log_filter.py
git commit -m "feat(api): expose dependency readiness and safe request logs"
```
