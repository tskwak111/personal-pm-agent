# Phase 5 — Google Calendar and External Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect Google Calendar with least privilege, import fixed events, write approved focus blocks through outbox, handle recurrence/timezone/deletion conflicts, and prove zero duplicate or false-success execution under injected failures.

**Architecture:** Auth and Calendar adapters sit behind provider ports. OAuth tokens are encrypted and versioned. Incoming sync creates external snapshots; outgoing commands are committed to outbox and executed by the worker with idempotency, retry classification and result verification.

**Tech Stack:** Authlib, Google Calendar API adapter, encrypted token vault, PostgreSQL outbox, Redis worker/scheduler, pytest and fault-injection fakes.

**Spec:** Design sections 11, 21, 23 and 25; Evaluation EXT-001 through EXT-007 and immediate stop criteria.

## Global Constraints

- Follow `AGENTS.md` and `docs/architecture/decision-precedence.md`.
- Never weaken Planner or Evaluation gates.
- Use TDD: failing test, confirmed failure, minimum implementation, focused pass, adjacent regression, commit.
- Every state change verifies workspace ownership and expected object version.
- External behavior is represented by ports and deterministic fakes in unit tests.
- Update `docs/status/IMPLEMENTATION_STATUS.md` after every completed Task.
- Do not claim completion without fresh command output.

---

## Locked File Map

```text
apps/api/src/personal_pm_api/calendar/
├─ oauth.py
├─ token_vault.py
├─ models.py
├─ schemas.py
├─ repository.py
├─ service.py
├─ sync.py
├─ focus_blocks.py
└─ router.py
apps/worker/src/personal_pm_worker/calendar/
├─ adapter.py
├─ executor.py
├─ retry.py
├─ sync_jobs.py
└─ scheduler.py
evals/fault-injection/calendar/
```

### Task P5-T01: Implement incremental OAuth connection and encrypted token vault

**Files:**
- Create: `apps/api/src/personal_pm_api/calendar/oauth.py`
- Create: `apps/api/src/personal_pm_api/calendar/token_vault.py`
- Create: `apps/api/src/personal_pm_api/calendar/router.py`
- Create: `apps/api/tests/integration/test_calendar_oauth.py`

**Interfaces:**
- Consumes: identity session, workspace ownership and encryption key settings
- Produces: PKCE/state/nonce OAuth flow, read-only first scope and separately authorized write scope

- [ ] **Step 1: Write the failing test**

```python
def test_oauth_callback_rejects_state_mismatch(auth_client, oauth_flow) -> None:
    response = auth_client.get("/api/v1/calendar/oauth/callback?code=x&state=wrong")
    assert response.status_code == 400
    assert response.json()["code"] == "OAUTH_STATE_MISMATCH"

def test_read_connection_does_not_request_write_scope(auth_client) -> None:
    response = auth_client.post("/api/v1/calendar/connections", json={"mode": "READ_ONLY"})
    assert "calendar.events" not in response.json()["authorization_url"]
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_calendar_oauth.py -q
```

Expected: FAIL because OAuth connection endpoints are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
class TokenVault:
    def encrypt(self, plaintext: str, key_version: int) -> EncryptedToken:
        nonce = os.urandom(12)
        ciphertext = AESGCM(self.keyring[key_version]).encrypt(nonce, plaintext.encode(), None)
        return EncryptedToken(ciphertext=ciphertext, nonce=nonce, key_version=key_version)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_calendar_oauth.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_identity_and_ownership.py apps/api/tests/integration/test_calendar_oauth.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/calendar/oauth.py apps/api/src/personal_pm_api/calendar/token_vault.py apps/api/src/personal_pm_api/calendar/router.py apps/api/tests/integration/test_calendar_oauth.py
git commit -m "feat(calendar): add least-privilege OAuth connection"
```

### Task P5-T02: Import external calendars and classify event availability effects

**Files:**
- Create: `apps/api/src/personal_pm_api/calendar/models.py`
- Create: `apps/api/src/personal_pm_api/calendar/repository.py`
- Create: `apps/api/src/personal_pm_api/calendar/sync.py`
- Create: `apps/worker/src/personal_pm_worker/calendar/adapter.py`
- Create: `apps/api/tests/integration/test_calendar_import.py`

**Interfaces:**
- Consumes: calendar connection and Planning availability contracts
- Produces: provider event snapshots mapped to Fixed Busy, Tentative, All-day Information or managed Focus Block

- [ ] **Step 1: Write the failing test**

```python
async def test_all_day_information_does_not_block_full_day(sync_service, provider_event_factory) -> None:
    event = provider_event_factory(all_day=True, transparency="transparent")
    imported = await sync_service.import_event(event)
    assert imported.availability_type == "ALL_DAY_INFORMATION"
    assert imported.blocks_capacity is False

async def test_same_external_id_updates_existing_record(sync_service, provider_event_factory) -> None:
    first = await sync_service.import_event(provider_event_factory(external_id="e1", title="old"))
    second = await sync_service.import_event(provider_event_factory(external_id="e1", title="new"))
    assert second.id == first.id
    assert await count_calendar_events(external_id="e1") == 1
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_calendar_import.py -q
```

Expected: FAIL because import mapping and external ID upsert are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
def classify_event(event: ProviderEvent) -> CalendarAvailabilityType:
    if event.managed_focus_block:
        return CalendarAvailabilityType.MOVABLE_COMMITMENT
    if event.all_day and not event.blocks_time:
        return CalendarAvailabilityType.ALL_DAY_INFORMATION
    if event.status == "tentative":
        return CalendarAvailabilityType.TENTATIVE
    return CalendarAvailabilityType.FIXED_BUSY
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_calendar_import.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_calendar_import.py apps/api/tests/integration/test_planning_service.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/calendar/models.py apps/api/src/personal_pm_api/calendar/repository.py apps/api/src/personal_pm_api/calendar/sync.py apps/worker/src/personal_pm_worker/calendar/adapter.py apps/api/tests/integration/test_calendar_import.py
git commit -m "feat(calendar): import fixed availability events"
```

### Task P5-T03: Handle recurrence, exceptions, tombstones, timezones and field ownership

**Files:**
- Create: `apps/api/src/personal_pm_api/calendar/field_ownership.py`
- Create: `apps/api/src/personal_pm_api/calendar/recurrence.py`
- Create: `apps/api/tests/integration/test_calendar_conflicts.py`

**Interfaces:**
- Consumes: external event snapshots and provider versions
- Produces: deterministic merge policy for recurring instances, external edits and deletions

- [ ] **Step 1: Write the failing test**

```python
async def test_external_deletion_creates_tombstone_not_immediate_hard_delete(sync_service, managed_focus_block) -> None:
    result = await sync_service.apply_provider_deletion(managed_focus_block.external_event_id)
    assert result.deleted_at is not None
    assert result.sync_status == "EXTERNALLY_DELETED"

async def test_external_focus_block_move_is_not_forced_back(sync_service, managed_focus_block) -> None:
    moved = await sync_service.apply_provider_update(managed_focus_block.provider_copy(start_delta_minutes=60))
    assert moved.pending_internal_reconciliation is True
    assert moved.outbound_restore_requested is False
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_calendar_conflicts.py -q
```

Expected: FAIL because recurrence and field ownership rules are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
FIELD_OWNER = {
    "external_title": "PROVIDER",
    "start_at": "LAST_EXPLICIT_USER_ACTION",
    "end_at": "LAST_EXPLICIT_USER_ACTION",
    "task_id": "PLANNING_CORE",
    "managed_marker": "PLANNING_CORE",
    "provider_version": "PROVIDER",
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_calendar_conflicts.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_calendar_import.py apps/api/tests/integration/test_calendar_conflicts.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/calendar/field_ownership.py apps/api/src/personal_pm_api/calendar/recurrence.py apps/api/tests/integration/test_calendar_conflicts.py
git commit -m "feat(calendar): reconcile recurrence and external edits"
```

### Task P5-T04: Create version-bound focus block proposals and approval flow

**Files:**
- Create: `apps/api/src/personal_pm_api/calendar/focus_blocks.py`
- Create: `apps/api/src/personal_pm_api/calendar/schemas.py`
- Create: `apps/api/tests/integration/test_focus_block_approval.py`

**Interfaces:**
- Consumes: Planner today output, authorization policy, Proposal and Approval records
- Produces: focus block simulation, approval binding and pending internal state

- [ ] **Step 1: Write the failing test**

```python
async def test_focus_block_creation_requires_approval(auth_client, ready_task) -> None:
    response = auth_client.post("/api/v1/calendar/focus-block-proposals", json={"task_id": str(ready_task.id), "start_at": "2026-08-24T11:00:00Z", "duration_minutes": 90, "expected_task_version": ready_task.version})
    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"

async def test_stale_task_version_invalidates_approval(approval_service, proposal, changed_task) -> None:
    result = await approval_service.approve(proposal.actor, proposal.id, proposal.version)
    assert result.status == "SUPERSEDED"
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_focus_block_approval.py -q
```

Expected: FAIL because focus block proposals are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
async def approve_focus_block(actor: CurrentActor, proposal: ProposalRecord, task: TaskRecord) -> OutboxRecord:
    if task.version != proposal.target_version:
        return await supersede(proposal, reason="TARGET_VERSION_CHANGED")
    command = ExternalCommand.create_focus_block(actor.workspace_id, proposal)
    return await enqueue_external_command(current_uow(), command)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_focus_block_approval.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_concurrency.py apps/api/tests/integration/test_focus_block_approval.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/calendar/focus_blocks.py apps/api/src/personal_pm_api/calendar/schemas.py apps/api/tests/integration/test_focus_block_approval.py
git commit -m "feat(calendar): approve focus block commands"
```

### Task P5-T05: Execute outbox commands idempotently and verify provider results

**Files:**
- Create: `apps/worker/src/personal_pm_worker/calendar/executor.py`
- Create: `apps/worker/src/personal_pm_worker/calendar/retry.py`
- Create: `apps/worker/tests/calendar/test_calendar_executor.py`

**Interfaces:**
- Consumes: outbox repository, token vault and provider adapter
- Produces: claim/execute/verify lifecycle with external ID and no false success

- [ ] **Step 1: Write the failing test**

```python
async def test_duplicate_delivery_creates_one_provider_event(executor, outbox_record, fake_calendar) -> None:
    await executor.execute(outbox_record.id)
    await executor.execute(outbox_record.id)
    assert fake_calendar.create_calls == 1
    assert await external_execution_status(outbox_record.id) == "SUCCEEDED"

async def test_timeout_after_provider_success_is_reconciled_without_duplicate(executor, timeout_after_success_record, fake_calendar) -> None:
    await executor.execute(timeout_after_success_record.id)
    await executor.execute(timeout_after_success_record.id)
    assert fake_calendar.create_calls == 1
    assert await external_event_id(timeout_after_success_record.id) is not None
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/worker/tests/calendar/test_calendar_executor.py -q
```

Expected: FAIL because the executor is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
async def execute(self, outbox_id: UUID) -> None:
    record = await self.repository.claim(outbox_id)
    existing = await self.repository.find_success_by_idempotency(record.idempotency_key)
    if existing is not None:
        await self.repository.link_existing_result(record, existing)
        return
    result = await self.adapter.execute(record.command)
    verified = await self.adapter.verify(result)
    await self.repository.finish(record.id, verified)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/worker/tests/calendar/test_calendar_executor.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/worker/tests/calendar -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/worker/src/personal_pm_worker/calendar/executor.py apps/worker/src/personal_pm_worker/calendar/retry.py apps/worker/tests/calendar/test_calendar_executor.py
git commit -m "feat(calendar): execute focus blocks idempotently"
```

### Task P5-T06: Classify retry, reauthorization and dead-letter outcomes

**Files:**
- Modify: `apps/worker/src/personal_pm_worker/calendar/retry.py`
- Create: `apps/worker/tests/calendar/test_retry_policy.py`

**Interfaces:**
- Consumes: provider error model and external execution states
- Produces: bounded exponential retry for transient errors and immediate reauthorization for expired credentials

- [ ] **Step 1: Write the failing test**

```python
from personal_pm_worker.calendar.retry import classify_failure

def test_oauth_expiration_never_retries_as_transient() -> None:
    decision = classify_failure(status_code=401, provider_code="invalid_grant", attempt=1)
    assert decision.action == "NEEDS_REAUTHORIZATION"
    assert decision.delay_seconds is None

def test_rate_limit_uses_bounded_backoff() -> None:
    decision = classify_failure(status_code=429, provider_code=None, attempt=3)
    assert decision.action == "RETRY"
    assert 1 <= decision.delay_seconds <= 900
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/worker/tests/calendar/test_retry_policy.py -q
```

Expected: FAIL because retry classification is missing.

- [ ] **Step 3: Implement the minimum contract**

```python
def classify_failure(status_code: int | None, provider_code: str | None, attempt: int) -> RetryDecision:
    if provider_code == "invalid_grant" or status_code == 401:
        return RetryDecision("NEEDS_REAUTHORIZATION", None)
    if status_code == 429 or (status_code is not None and status_code >= 500):
        return RetryDecision("RETRY", min(900, 2 ** attempt + deterministic_jitter(attempt)))
    return RetryDecision("DEAD_LETTER", None)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/worker/tests/calendar/test_retry_policy.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/worker/tests/calendar -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/worker/src/personal_pm_worker/calendar/retry.py apps/worker/tests/calendar/test_retry_policy.py
git commit -m "feat(calendar): classify execution failures"
```

### Task P5-T07: Add webhook and periodic reconciliation scheduling

**Files:**
- Create: `apps/worker/src/personal_pm_worker/calendar/sync_jobs.py`
- Create: `apps/worker/src/personal_pm_worker/calendar/scheduler.py`
- Create: `apps/worker/tests/calendar/test_sync_recovery.py`

**Interfaces:**
- Consumes: Calendar adapter, sync cursor and Redis scheduler
- Produces: webhook-triggered delta sync plus 15-minute recovery polling when webhook is missed

- [ ] **Step 1: Write the failing test**

```python
async def test_missed_webhook_is_recovered_within_periodic_window(sync_scheduler, fake_clock, changed_provider_event) -> None:
    fake_clock.advance(minutes=15)
    await sync_scheduler.run_due()
    assert await internal_event_version(changed_provider_event.external_id) == changed_provider_event.version

async def test_duplicate_webhook_uses_same_operation(sync_scheduler, webhook_payload) -> None:
    first = await sync_scheduler.accept_webhook(webhook_payload)
    second = await sync_scheduler.accept_webhook(webhook_payload)
    assert second.operation_id == first.operation_id
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/worker/tests/calendar/test_sync_recovery.py -q
```

Expected: FAIL because sync scheduling is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
SYNC_RECOVERY_INTERVAL = timedelta(minutes=15)

async def accept_webhook(self, payload: WebhookPayload) -> SyncOperation:
    operation_key = f"calendar-sync:{payload.channel_id}:{payload.resource_state}:{payload.message_number}"
    return await self.operations.get_or_create(operation_key, payload.connection_id)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/worker/tests/calendar/test_sync_recovery.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/worker/tests/calendar apps/api/tests/integration/test_calendar_conflicts.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/worker/src/personal_pm_worker/calendar/sync_jobs.py apps/worker/src/personal_pm_worker/calendar/scheduler.py apps/worker/tests/calendar/test_sync_recovery.py
git commit -m "feat(calendar): recover missed synchronization"
```

### Task P5-T08: Automate Stage C fault-injection gates

**Files:**
- Create: `evals/fault-injection/calendar/scenarios.yaml`
- Create: `scripts/run_calendar_faults.py`
- Create: `apps/worker/tests/evals/test_calendar_fault_runner.py`

**Interfaces:**
- Consumes: calendar fake adapter, worker and Evaluation EXT metrics
- Produces: repeatable timeout, 429, 5xx, OAuth expiry, duplicate worker and crash-window scenarios with machine-readable report

- [ ] **Step 1: Write the failing test**

```python
from scripts.run_calendar_faults import run_fault_scenarios

def test_fault_report_has_zero_duplicate_and_false_success(sample_fault_suite) -> None:
    report = run_fault_scenarios(sample_fault_suite)
    assert report.metrics["EXT-002"].failures == 0
    assert report.metrics["EXT-003"].failures == 0
    assert report.metrics["EXT-006"].failures == 0
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/worker/tests/evals/test_calendar_fault_runner.py -q
```

Expected: FAIL because fault scenario runner is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
REQUIRED_SCENARIOS = (
    "api-timeout",
    "rate-limit-429",
    "provider-5xx",
    "oauth-expired",
    "duplicate-worker-delivery",
    "crash-after-db-commit",
    "provider-success-response-lost",
)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/worker/tests/evals/test_calendar_fault_runner.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run python scripts/run_calendar_faults.py --output evals/reports/calendar-stage-c.json
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add evals/fault-injection/calendar/scenarios.yaml scripts/run_calendar_faults.py apps/worker/tests/evals/test_calendar_fault_runner.py
git commit -m "test(evals): automate Calendar fault gates"
```

## Phase 5 Exit Criteria

- [ ] Read and write Calendar scopes are separately authorized.
- [ ] Refresh tokens are encrypted, versioned and absent from logs.
- [ ] Recurrence, external deletion, timezone and external moves have contract tests.
- [ ] One idempotency key creates at most one provider event.
- [ ] Internal pending, external success, external failure and reauthorization are distinct states.
- [ ] All required Stage C fault scenarios produce zero duplicate and zero false success.
