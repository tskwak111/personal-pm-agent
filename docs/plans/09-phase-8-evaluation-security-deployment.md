# Phase 8 — Evaluation, Security, Observability, Deployment and Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce reproducible Stage A–C release evidence, harden security and privacy, add observability, containerized deployment, backup/restore and the exact instrumentation needed for the controlled user pilot.

**Architecture:** Versioned event schemas feed automated metric calculators and reports. Security controls are tested as product requirements. Deployments use separate Web/API/Worker processes and managed-compatible data services. Pilot tooling records baseline and agent-use outcomes without changing gates after results are known.

**Tech Stack:** OpenTelemetry, structured logs, Prometheus-compatible metrics, pytest/Hypothesis, Playwright, security scanners, Docker, deployment manifests, PostgreSQL backup tools and report generators.

**Spec:** Entire Evaluation and Pilot Plan plus Design sections 24–30.

## Global Constraints

- Follow `AGENTS.md`, the approved specs and exact Phase interface contracts.
- LLMs generate candidates and language; deterministic services authorize and execute.
- User-facing state must distinguish fact, inference, proposal, internal execution and external execution.
- Use TDD and fresh verification before every completion claim.
- Update implementation status and traceability after every Task.

---

## Locked File Map

```text
apps/api/src/personal_pm_api/telemetry/
apps/api/src/personal_pm_api/security/
evals/{golden,planner-vectors,expert-scenarios,fault-injection,reports}/
scripts/{run_stage_a.py,run_stage_b.py,run_stage_c.py,build_release_report.py}
infra/{docker,deployment,monitoring,backup}/
docs/operations/
docs/pilot/
```

### Task P8-T01: Define versioned telemetry and metric event schemas

**Files:**
- Create: `apps/api/src/personal_pm_api/telemetry/events.py`
- Create: `apps/api/src/personal_pm_api/telemetry/emitter.py`
- Create: `apps/api/tests/unit/test_telemetry_events.py`
- Create: `docs/operations/event-catalog.md`

**Interfaces:**
- Consumes: Evaluation Metric IDs and operation data
- Produces: privacy-safe events for Planner, LLM, external execution, UX and pilot outcomes

- [ ] **Step 1: Write the failing test**

```python
def test_event_schema_rejects_sensitive_fields() -> None:
    with pytest.raises(SensitiveTelemetryFieldError):
        PlannerRunEvent(trace_id="t", workspace_hash="w", document_text="secret")

def test_metric_events_include_version_dimensions() -> None:
    event = planner_run_event_factory()
    assert event.planner_version
    assert event.code_version
    assert event.schema_version == 1
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/unit/test_telemetry_events.py -q
```

Expected: FAIL because telemetry events are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
SENSITIVE_FIELD_NAMES = {"document_text", "oauth_token", "prompt_text", "personal_note", "calendar_description"}

@dataclass(frozen=True, slots=True)
class PlannerRunEvent:
    schema_version: int
    trace_id: str
    workspace_hash: str
    code_version: str
    planner_version: str
    input_size: int
    latency_ms: int
    result: str
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/unit/test_telemetry_events.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/unit/test_telemetry_events.py apps/api/tests/integration/test_agent_operations.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/telemetry/events.py apps/api/src/personal_pm_api/telemetry/emitter.py apps/api/tests/unit/test_telemetry_events.py docs/operations/event-catalog.md
git commit -m "feat(telemetry): define privacy-safe event catalog"
```

### Task P8-T02: Automate Stage A domain, safety, property and performance report

**Files:**
- Create: `scripts/run_stage_a.py`
- Create: `evals/reports/schema/stage-a.schema.json`
- Create: `packages/planner/tests/properties/test_generated_scenarios.py`
- Create: `packages/planner/tests/performance/test_reference_environment.py`
- Create: `apps/api/tests/evals/test_stage_a_runner.py`

**Interfaces:**
- Consumes: Planner tests, SAFE/PLAN Metric IDs and reference environment
- Produces: single Stage A command that runs 20,000 scenarios and emits per-Gate counts

- [ ] **Step 1: Write the failing test**

```python
from scripts.run_stage_a import build_stage_a_report

def test_stage_a_fails_on_one_invariant_violation(fake_test_results) -> None:
    fake_test_results.add_failure("PLAN-001")
    report = build_stage_a_report(fake_test_results)
    assert report.overall == "FAIL"
    assert report.gates["PLAN-001"].failures == 1

def test_stage_a_records_reference_environment(fake_test_results) -> None:
    report = build_stage_a_report(fake_test_results)
    assert report.environment.python_version
    assert report.environment.cpu_model
    assert report.environment.memory_bytes > 0
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/evals/test_stage_a_runner.py -q
```

Expected: FAIL because the Stage A runner is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
HARD_GATES = {
    "SAFE-001", "SAFE-002", "SAFE-003", "SAFE-004", "SAFE-005", "SAFE-006",
    "PLAN-001", "PLAN-002", "PLAN-003", "PLAN-004", "PLAN-005",
    "PLAN-006", "PLAN-007", "PLAN-008", "PLAN-009",
}

def overall_stage_a(gates: Mapping[str, GateResult]) -> str:
    return "PASS" if all(gates[gate].passed for gate in HARD_GATES) else "FAIL"
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/evals/test_stage_a_runner.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run python scripts/run_stage_a.py --scenarios 20000 --output evals/reports/stage-a.json
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add scripts/run_stage_a.py evals/reports/schema/stage-a.schema.json packages/planner/tests/properties/test_generated_scenarios.py packages/planner/tests/performance/test_reference_environment.py apps/api/tests/evals/test_stage_a_runner.py
git commit -m "test(evals): automate Stage A gates"
```

### Task P8-T03: Complete Stage B golden and expert scenario evaluation

**Files:**
- Create: `evals/expert-scenarios/schema.json`
- Create: `evals/expert-scenarios/sample.jsonl`
- Create: `scripts/run_stage_b.py`
- Create: `apps/api/tests/evals/test_stage_b_metrics.py`
- Create: `docs/pilot/annotation-guide.md`

**Interfaces:**
- Consumes: golden intake runner, Planner and Evaluation AI/PQ metrics
- Produces: precision/recall, auto-registration error, Macro F1, P0/P1 recall and approval accuracy report

- [ ] **Step 1: Write the failing test**

```python
from scripts.run_stage_b import compute_precision_recall, build_stage_b_report

def test_precision_recall_uses_fixed_gold_denominator() -> None:
    result = compute_precision_recall(true_positive=95, false_positive=1, false_negative=5)
    assert result.precision == pytest.approx(95 / 96)
    assert result.recall == pytest.approx(95 / 100)

def test_required_metric_below_threshold_fails_stage(sample_stage_b_counts) -> None:
    sample_stage_b_counts["AI-010"] = 0.98
    assert build_stage_b_report(sample_stage_b_counts).overall == "FAIL"
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/evals/test_stage_b_metrics.py -q
```

Expected: FAIL because Stage B metric calculators are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
REQUIRED_THRESHOLDS = {
    "AI-001": 0.985,
    "AI-002": 0.995,
    "AI-010": 0.990,
    "AI-011": 0.950,
    "AI-012": 0.995,
    "AI-013": 0.980,
    "PQ-RISK-MACRO-F1": 0.900,
    "PQ-P0-P1-RECALL": 0.980,
    "PQ-AUTH-ACCURACY": 1.000,
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/evals/test_stage_b_metrics.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run python scripts/run_stage_b.py --golden evals/golden --expert evals/expert-scenarios --output evals/reports/stage-b.json
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add evals/expert-scenarios/schema.json evals/expert-scenarios/sample.jsonl scripts/run_stage_b.py apps/api/tests/evals/test_stage_b_metrics.py docs/pilot/annotation-guide.md
git commit -m "test(evals): automate Stage B quality metrics"
```

### Task P8-T04: Automate Stage C external and resilience report

**Files:**
- Create: `scripts/run_stage_c.py`
- Create: `evals/reports/schema/stage-c.schema.json`
- Create: `apps/worker/tests/evals/test_stage_c_runner.py`

**Interfaces:**
- Consumes: Calendar fault runner, outbox telemetry and EXT metrics
- Produces: external write success, duplicate, false-success, reauthorization, recovery latency and outbox-loss report

- [ ] **Step 1: Write the failing test**

```python
from scripts.run_stage_c import build_stage_c_report

def test_any_duplicate_external_event_fails_stage_c(sample_ext_results) -> None:
    sample_ext_results["EXT-002"].failures = 1
    assert build_stage_c_report(sample_ext_results).overall == "FAIL"

def test_recovery_window_threshold_is_fifteen_minutes(sample_ext_results) -> None:
    sample_ext_results["webhook_recovery_seconds"].p95 = 901
    assert build_stage_c_report(sample_ext_results).overall == "FAIL"
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/worker/tests/evals/test_stage_c_runner.py -q
```

Expected: FAIL because Stage C aggregation is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
ZERO_FAILURE_EXT_GATES = {"EXT-002", "EXT-003", "EXT-004", "EXT-005", "EXT-006", "EXT-007"}

def build_stage_c_report(results: StageCInputs) -> StageCReport:
    zero_gate_pass = all(results[metric].failures == 0 for metric in ZERO_FAILURE_EXT_GATES)
    success_rate_pass = results["EXT-001"].rate >= 0.995
    recovery_pass = results["webhook_recovery_seconds"].p95 <= 900
    return StageCReport(overall="PASS" if zero_gate_pass and success_rate_pass and recovery_pass else "FAIL")
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/worker/tests/evals/test_stage_c_runner.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run python scripts/run_stage_c.py --output evals/reports/stage-c.json
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add scripts/run_stage_c.py evals/reports/schema/stage-c.schema.json apps/worker/tests/evals/test_stage_c_runner.py
git commit -m "test(evals): automate Stage C report"
```

### Task P8-T05: Harden auth, CSRF, rate limits, file scanning and prompt-injection boundaries

**Files:**
- Create: `apps/api/src/personal_pm_api/security/csrf.py`
- Create: `apps/api/src/personal_pm_api/security/rate_limit.py`
- Create: `apps/api/src/personal_pm_api/security/uploads.py`
- Create: `apps/api/tests/security/test_security_controls.py`
- Create: `apps/worker/tests/security/test_prompt_injection_boundary.py`

**Interfaces:**
- Consumes: session, upload, LLM and execution flows
- Produces: tested security middleware and explicit tool-less untrusted extraction path

- [ ] **Step 1: Write the failing test**

```python
def test_mutating_request_without_csrf_is_rejected(auth_client) -> None:
    response = auth_client.post("/api/v1/tasks", json={"title": "x"}, headers={"X-CSRF-Token": ""})
    assert response.status_code == 403

async def test_document_instruction_cannot_create_external_command(extraction_pipeline, malicious_document) -> None:
    result = await extraction_pipeline.process(malicious_document)
    assert result.requested_actions == ()
    assert await count_outbox_events() == 0

def test_llm_rate_limit_is_separate_from_read_api(rate_limiter, actor) -> None:
    exhaust(rate_limiter, actor, bucket="llm")
    assert rate_limiter.allow(actor, bucket="read-api") is True
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/security/test_security_controls.py apps/worker/tests/security/test_prompt_injection_boundary.py -q
```

Expected: FAIL because security controls are incomplete.

- [ ] **Step 3: Implement the minimum contract**

```python
RATE_LIMITS = {
    "auth": RateLimit(10, timedelta(minutes=10)),
    "upload": RateLimit(20, timedelta(hours=1)),
    "llm": RateLimit(100, timedelta(days=1)),
    "external-write": RateLimit(30, timedelta(hours=1)),
    "read-api": RateLimit(600, timedelta(minutes=10)),
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/security/test_security_controls.py apps/worker/tests/security/test_prompt_injection_boundary.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pip-audit && pnpm audit --prod
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/security/csrf.py apps/api/src/personal_pm_api/security/rate_limit.py apps/api/src/personal_pm_api/security/uploads.py apps/api/tests/security/test_security_controls.py apps/worker/tests/security/test_prompt_injection_boundary.py
git commit -m "feat(security): enforce product security boundaries"
```

### Task P8-T06: Add structured logging, tracing, metrics and SLO dashboards

**Files:**
- Create: `apps/api/src/personal_pm_api/telemetry/logging.py`
- Create: `apps/api/src/personal_pm_api/telemetry/tracing.py`
- Create: `infra/monitoring/dashboards/api.json`
- Create: `infra/monitoring/dashboards/planner.json`
- Create: `infra/monitoring/alerts.yaml`
- Create: `apps/api/tests/unit/test_sensitive_log_filter.py`

**Interfaces:**
- Consumes: telemetry event catalog and runtime services
- Produces: trace propagation, sensitive-field filter, API/Planner/LLM/Calendar metrics and alert rules

- [ ] **Step 1: Write the failing test**

```python
def test_sensitive_values_are_redacted(structured_logger) -> None:
    event = structured_logger.bind(oauth_token="secret", document_text="private", trace_id="t").capture("test")
    assert event["oauth_token"] == "[REDACTED]"
    assert event["document_text"] == "[REDACTED]"

def test_workspace_identifier_is_hashed(structured_logger) -> None:
    event = structured_logger.bind(workspace_id="00000000-0000-0000-0000-000000000001").capture("test")
    assert event["workspace_hash"] != "00000000-0000-0000-0000-000000000001"
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/unit/test_sensitive_log_filter.py -q
```

Expected: FAIL because logging filters and dashboards are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
SENSITIVE_KEYS = frozenset({"oauth_token", "refresh_token", "document_text", "prompt_text", "personal_note", "calendar_description"})

def sanitize_log_fields(fields: Mapping[str, object]) -> dict[str, object]:
    return {key: "[REDACTED]" if key in SENSITIVE_KEYS else value for key, value in fields.items()}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/unit/test_sensitive_log_filter.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/unit/test_telemetry_events.py apps/api/tests/unit/test_sensitive_log_filter.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/telemetry/logging.py apps/api/src/personal_pm_api/telemetry/tracing.py infra/monitoring/dashboards/api.json infra/monitoring/dashboards/planner.json infra/monitoring/alerts.yaml apps/api/tests/unit/test_sensitive_log_filter.py
git commit -m "feat(observability): add privacy-safe telemetry"
```

### Task P8-T07: Create production containers and deployment configuration

**Files:**
- Create: `infra/docker/Dockerfile.api`
- Create: `infra/docker/Dockerfile.worker`
- Create: `infra/docker/Dockerfile.web`
- Create: `infra/deployment/api.yaml`
- Create: `infra/deployment/worker.yaml`
- Create: `infra/deployment/web.yaml`
- Create: `infra/deployment/migrate.yaml`
- Create: `scripts/smoke_deployment.py`

**Interfaces:**
- Consumes: built applications, environment contract and health endpoints
- Produces: non-root reproducible images, explicit migration job and smoke test

- [ ] **Step 1: Write the failing test**

```python
from scripts.smoke_deployment import validate_image_contract

def test_images_run_as_non_root(container_metadata) -> None:
    for image in container_metadata.images:
        assert validate_image_contract(image).user not in {"", "0", "root"}

def test_migration_is_separate_from_api_start(deployment_manifests) -> None:
    assert deployment_manifests.api.command != deployment_manifests.migrate.command
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/evals/test_deployment_contract.py -q
```

Expected: FAIL because production images and manifests are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
# Dockerfile.api excerpt
FROM python:3.13-slim AS runtime
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY apps/api/src /app/apps/api/src
USER app
CMD ["/app/.venv/bin/uvicorn", "personal_pm_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/evals/test_deployment_contract.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
docker build -f infra/docker/Dockerfile.api . && docker build -f infra/docker/Dockerfile.worker . && docker build -f infra/docker/Dockerfile.web .
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add infra/docker/Dockerfile.api infra/docker/Dockerfile.worker infra/docker/Dockerfile.web infra/deployment/api.yaml infra/deployment/worker.yaml infra/deployment/web.yaml infra/deployment/migrate.yaml scripts/smoke_deployment.py
git commit -m "chore(deploy): add production process images"
```

### Task P8-T08: Implement backup, restore, retention and deletion verification

**Files:**
- Create: `infra/backup/backup-postgres.sh`
- Create: `infra/backup/restore-postgres.sh`
- Create: `infra/backup/verify-object-retention.py`
- Create: `scripts/test_backup_restore.py`
- Create: `docs/operations/backup-and-restore.md`

**Interfaces:**
- Consumes: PostgreSQL, object storage and user deletion requirements
- Produces: encrypted backup, point-in-time-compatible procedure, restore test and deletion propagation report

- [ ] **Step 1: Write the failing test**

```python
from scripts.test_backup_restore import run_backup_restore_test

def test_backup_restore_preserves_plan_and_audit_links(test_environment) -> None:
    result = run_backup_restore_test(test_environment)
    assert result.restored_plan_count == result.source_plan_count
    assert result.broken_audit_references == 0

def test_deleted_source_is_absent_after_retention_window(retention_verifier, deleted_source) -> None:
    result = retention_verifier.verify(deleted_source.id)
    assert result.primary_object_absent is True
    assert result.backup_expiry_at is not None
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/evals/test_backup_restore.py -q
```

Expected: FAIL because backup and restore tooling are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
def verify_restore(source_counts: Counts, restored_counts: Counts, broken_references: int) -> RestoreResult:
    return RestoreResult(
        counts_match=source_counts == restored_counts,
        broken_references=broken_references,
        passed=source_counts == restored_counts and broken_references == 0,
    )
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/evals/test_backup_restore.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run python scripts/test_backup_restore.py --compose compose.yaml
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add infra/backup/backup-postgres.sh infra/backup/restore-postgres.sh infra/backup/verify-object-retention.py scripts/test_backup_restore.py docs/operations/backup-and-restore.md
git commit -m "chore(operations): verify backup and restore"
```

### Task P8-T09: Create controlled pilot consent, baseline, survey and incident workflows

**Files:**
- Create: `docs/pilot/participant-protocol.md`
- Create: `docs/pilot/baseline-questionnaire.md`
- Create: `docs/pilot/weekly-survey.md`
- Create: `docs/pilot/incident-procedure.md`
- Create: `apps/api/src/personal_pm_api/analytics/pilot.py`
- Create: `apps/api/tests/integration/test_pilot_metrics.py`

**Interfaces:**
- Consumes: Evaluation Stage D and telemetry events
- Produces: participant enrollment, baseline week, four agent weeks, outcome calculations and immediate-stop workflow

- [ ] **Step 1: Write the failing test**

```python
async def test_active_user_definition_requires_behavior_not_login(pilot_metrics, login_only_participant) -> None:
    result = await pilot_metrics.week_four_active(login_only_participant.id)
    assert result is False

async def test_system_caused_deadline_delay_is_never_averaged_away(pilot_metrics, critical_incident) -> None:
    report = await pilot_metrics.build_outcome_report()
    assert report.system_caused_deadline_delays == 1
    assert report.release_eligible is False
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_pilot_metrics.py -q
```

Expected: FAIL because pilot metric definitions are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
def week_four_active(days_used: int, task_actions: int, plan_views: int) -> bool:
    return days_used >= 3 and task_actions >= 5 and plan_views >= 2

MANDATORY_OUTCOMES = {"OUT-001", "OUT-002", "OUT-005", "OUT-006"}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_pilot_metrics.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_pilot_metrics.py apps/api/tests/unit/test_telemetry_events.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add docs/pilot/participant-protocol.md docs/pilot/baseline-questionnaire.md docs/pilot/weekly-survey.md docs/pilot/incident-procedure.md apps/api/src/personal_pm_api/analytics/pilot.py apps/api/tests/integration/test_pilot_metrics.py
git commit -m "feat(pilot): instrument controlled user evaluation"
```

### Task P8-T10: Build final release report, immutable gate decision and repository audit

**Files:**
- Create: `scripts/build_release_report.py`
- Create: `scripts/verify_release.py`
- Create: `docs/operations/release-runbook.md`
- Create: `apps/api/tests/evals/test_release_decision.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: Stage A/B/C reports, security results, deployment smoke and pilot report
- Produces: Pass/Conditional Pass/Fail decision that cannot lower thresholds after results

- [ ] **Step 1: Write the failing test**

```python
from scripts.verify_release import decide_release

def test_one_s0_incident_always_fails_release(release_inputs) -> None:
    release_inputs.s0_incidents = 1
    assert decide_release(release_inputs).decision == "FAIL"

def test_required_outcome_failure_cannot_be_conditional_pass(release_inputs) -> None:
    release_inputs.outcomes["OUT-001"].passed = False
    assert decide_release(release_inputs).decision == "FAIL"

def test_threshold_change_after_evaluation_is_rejected(release_inputs) -> None:
    release_inputs.threshold_changes[0].changed_before_or_after_evaluation = "AFTER"
    assert decide_release(release_inputs).decision == "FAIL"
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/evals/test_release_decision.py -q
```

Expected: FAIL because release decision logic is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
def decide_release(inputs: ReleaseInputs) -> ReleaseDecision:
    if inputs.s0_incidents or inputs.system_caused_deadline_delays:
        return ReleaseDecision("FAIL", ("CATASTROPHIC_GATE",))
    if any(change.changed_before_or_after_evaluation == "AFTER" for change in inputs.threshold_changes):
        return ReleaseDecision("FAIL", ("POST_HOC_THRESHOLD_CHANGE",))
    if not inputs.stage_a.passed or not inputs.stage_b.required_passed or not inputs.stage_c.passed:
        return ReleaseDecision("FAIL", ("TECHNICAL_GATE_FAILED",))
    if not all(inputs.outcomes[metric].passed for metric in MANDATORY_OUTCOMES):
        return ReleaseDecision("FAIL", ("MANDATORY_OUTCOME_FAILED",))
    passed_count = sum(result.passed for result in inputs.outcomes.values())
    return ReleaseDecision("PASS" if passed_count >= 8 else "CONDITIONAL_PASS", ())
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/evals/test_release_decision.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
make verify && make stage-a && make stage-b && make stage-c && make release-report
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add scripts/build_release_report.py scripts/verify_release.py docs/operations/release-runbook.md apps/api/tests/evals/test_release_decision.py Makefile
git commit -m "test(release): enforce immutable release decision"
```

## Phase 8 Exit Criteria

- [ ] Stage A, B and C commands generate versioned machine-readable reports. — BLOCKED_EXTERNAL: Stage B private holdout and Stage C live-provider inputs are absent.
- [x] Security tests cover bearer-only auth/CSRF posture, ownership, rate limit, file safety and prompt injection.
- [x] Logs and traces redact sensitive fields.
- [x] Production images run as non-root and migrations are separate jobs.
- [ ] Backup and restore are executed, not merely documented. — BLOCKED_EXTERNAL: managed restore RPO/RTO drill is absent.
- [x] Pilot protocol and outcome definitions match the evaluation spec.
- [x] Release decision cannot be altered by post-hoc threshold changes.
- [ ] `make verify`, Stage A–C and release report commands all pass from a clean checkout. — BLOCKED_EXTERNAL: mandatory private/live/pilot inputs prevent a release PASS.
