# Truthful Evaluation and Release Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Stage A–C, backup/restore, and release commands measure their claims and fail closed.

**Architecture:** Gate runners consume explicit machine-readable observations. Missing observations are failures or `BLOCKED_EXTERNAL`, never inferred success; every non-pass process exits non-zero.

**Tech Stack:** Python 3.13 stdlib, pytest, Hypothesis, JSON Schema, Make

**Spec:** `docs/superpowers/specs/2026-08-31-aaa-production-readiness-design.md`

## Global Constraints

- Thresholds and denominators come from the normative evaluation specification.
- Stage A must run exactly the requested generated scenario count.
- Missing mandatory evidence is non-releaseable.
- Live credentials, private corpora, deployment, and user-pilot evidence use `BLOCKED_EXTERNAL`.
- Runners emit revision, input hash, denominator, timestamp, environment, and command result.

---

### Task 1: Attribute real Stage A observations

**Files:**
- Modify: `scripts/run_stage_a.py`
- Modify: `packages/planner/tests/properties/test_generated_scenarios.py`
- Create: `evals/planner-vectors/gate-test-map.json`
- Modify: `evals/reports/schema/stage-a.schema.json`
- Test: `apps/api/tests/evals/test_stage_a_runner.py`

**Interfaces:**
- Produces: one observation per `HARD_GATES` entry with `executed`, `checks`, `failures`, and `source`
- Produces: `run_stage_a.py --scenarios N` that executes N generated examples and exits 1 on any missing/failed gate

- [ ] **Step 1: Write failing tests for unexecuted gates and scenario forwarding**

```python
def test_unexecuted_gate_cannot_pass() -> None:
    report = build_stage_a_report(FakeTestResults(executed={"PLAN-001"}), scenarios=25)
    assert report.overall == "FAIL"
    assert report.gates["PLAN-002"].passed is False

def test_property_command_receives_requested_count() -> None:
    command = property_command(37, Path("observations.json"))
    assert ["--scenarios", "37"] == command[-4:-2]
```

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/evals/test_stage_a_runner.py -q`

Expected: FAIL because the current source reports zero failures for unexecuted gates and ignores `--scenarios`.

- [ ] **Step 3: Emit observations from the generated runner**

Add CLI arguments `--scenarios` and `--observations` to the property module. Use a deterministic seed and write:

```json
{"scenario_count":37,"gates":{"PLAN-002":{"executed":true,"checks":37,"failures":0}}}
```

The gate map lists exact pytest nodes for SAFE-001..006 and PLAN-001..009. Stage A runs those nodes plus generated scenarios; a subprocess failure marks only its mapped gates failed and records stderr.

- [ ] **Step 4: Validate completeness and schema**

```python
missing = set(HARD_GATES) - set(observations)
overall = "PASS" if not missing and all(item.executed and item.failures == 0 for item in observations.values()) else "FAIL"
```

- [ ] **Step 5: Verify positive and negative execution**

```bash
uv run pytest apps/api/tests/evals/test_stage_a_runner.py packages/planner/tests/properties -q
uv run python scripts/run_stage_a.py --scenarios 25 --output /tmp/pma-stage-a.json
```

Use a test fixture with one omitted gate and assert runner exit code 1.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_stage_a.py packages/planner/tests/properties/test_generated_scenarios.py evals/planner-vectors/gate-test-map.json evals/reports/schema/stage-a.schema.json apps/api/tests/evals/test_stage_a_runner.py
git commit -m "test(evals): measure every Stage A gate"
```

### Task 2: Enforce Stage B completeness and blocked status

**Files:**
- Modify: `scripts/run_stage_b.py`
- Modify: `evals/golden/README.md`
- Create: `evals/expert-scenarios/README.md`
- Test: `apps/api/tests/evals/test_stage_b_metrics.py`

**Interfaces:**
- Produces: `StageBReport(overall: Literal["PASS","FAIL","BLOCKED_EXTERNAL"], metrics, denominators)`
- Requires: 200 golden sources, 150 expert scenarios, and every required metric

- [ ] **Step 1: Write failing completeness tests**

```python
def test_missing_required_metric_is_not_coerced_to_zero(sample_stage_b_counts) -> None:
    del sample_stage_b_counts["AI-010"]
    report = build_stage_b_report(sample_stage_b_counts, golden_count=200, expert_count=150)
    assert report.overall == "FAIL"
    assert report.metrics["AI-010"]["status"] == "MISSING"

def test_small_private_corpus_is_blocked(sample_stage_b_counts) -> None:
    report = build_stage_b_report(sample_stage_b_counts, golden_count=3, expert_count=2)
    assert report.overall == "BLOCKED_EXTERNAL"
```

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/evals/test_stage_b_metrics.py -q`

- [ ] **Step 3: Parse real denominators**

Count valid JSONL records, reject malformed or duplicate IDs, require explicit `counts.json` keys, and record:

```python
denominators = {"golden_sources": golden_count, "expert_scenarios": expert_count}
if golden_count < 200 or expert_count < 150:
    overall = "BLOCKED_EXTERNAL"
elif missing_metrics or threshold_failures:
    overall = "FAIL"
else:
    overall = "PASS"
```

- [ ] **Step 4: Return truthful process status**

Return 0 only for PASS. Return 2 for `BLOCKED_EXTERNAL` and 1 for FAIL.

- [ ] **Step 5: Verify**

```bash
uv run pytest apps/api/tests/evals/test_stage_b_metrics.py apps/worker/tests/evals/test_golden_runner.py -q
uv run python scripts/run_stage_b.py --golden evals/golden --expert evals/expert-scenarios --output /tmp/pma-stage-b.json
test $? -eq 2
```

- [ ] **Step 6: Commit**

```bash
git add scripts/run_stage_b.py evals/golden/README.md evals/expert-scenarios/README.md apps/api/tests/evals/test_stage_b_metrics.py
git commit -m "test(evals): block incomplete Stage B evidence"
```

### Task 3: Derive every Stage C metric from fault observations

**Files:**
- Modify: `scripts/run_calendar_faults.py`
- Modify: `scripts/run_stage_c.py`
- Modify: `evals/fault-injection/calendar/scenarios.yaml`
- Modify: `evals/reports/schema/stage-c.schema.json`
- Test: `apps/worker/tests/evals/test_calendar_fault_runner.py`
- Test: `apps/worker/tests/evals/test_stage_c_runner.py`

**Interfaces:**
- Consumes: fault results containing metric IDs and measured recovery seconds
- Produces: complete EXT-001..007 observations and `webhook_recovery_seconds.p95`

- [ ] **Step 1: Write failing missing-evidence tests**

```python
def test_missing_ext_metric_fails_without_key_error(sample_ext_results) -> None:
    del sample_ext_results["EXT-004"]
    report = build_stage_c_report(sample_ext_results)
    assert report.overall == "FAIL"
    assert report.detail["missing_metrics"] == ["EXT-004"]
```

Add a CLI test where the fault runner exits non-zero and assert Stage C exits 1.

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/worker/tests/evals/test_stage_c_runner.py -q`

- [ ] **Step 3: Replace default-zero gates**

Every fault scenario declares `metric_ids`. Aggregate only observed results:

```python
required = {"EXT-001", *ZERO_FAILURE_EXT_GATES, "webhook_recovery_seconds"}
missing = sorted(required - results.keys())
if missing:
    return StageCReport("FAIL", {"missing_metrics": missing})
```

Do not construct `ExtGateResult(failures=0)` for metrics absent from the fault report.

- [ ] **Step 4: Verify clean and injected-failure reports**

```bash
uv run pytest apps/worker/tests/evals/test_calendar_fault_runner.py apps/worker/tests/evals/test_stage_c_runner.py -q
uv run python scripts/run_stage_c.py --output /tmp/pma-stage-c.json
```

The local no-provider profile must return `BLOCKED_EXTERNAL` with exit 2 unless all provider observations came from a declared emulator.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_calendar_faults.py scripts/run_stage_c.py evals/fault-injection/calendar/scenarios.yaml evals/reports/schema/stage-c.schema.json apps/worker/tests/evals
git commit -m "test(evals): derive Stage C from fault evidence"
```

### Task 4: Make backup/restore verification executable

**Files:**
- Modify: `infra/backup/backup-postgres.sh`
- Modify: `infra/backup/restore-postgres.sh`
- Modify: `scripts/test_backup_restore.py`
- Modify: `apps/api/tests/evals/test_backup_restore.py`
- Modify: `docs/operations/backup-and-restore.md`

**Interfaces:**
- Produces: source/restored counts and broken audit-reference query results
- Produces: exit 0 PASS, exit 1 FAIL, exit 2 `BLOCKED_EXTERNAL`

- [ ] **Step 1: Write a process-level failing test**

```python
def test_main_without_database_reports_blocked(capsys) -> None:
    assert main(["--compose", "compose.yaml"]) == 2
    assert "BLOCKED_EXTERNAL" in capsys.readouterr().out
```

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/evals/test_backup_restore.py -q`

- [ ] **Step 3: Execute isolated source and restored database checks**

Require explicit `--source-url`, `--restore-url`, `--backup-file`, and `--now-utc`. Call existing shell scripts with `subprocess.run(..., check=True)`, query plan/audit counts with psycopg, and fail when restored counts differ or audit references break. Do not use `datetime.now()` in retention results.

- [ ] **Step 4: Verify unit contract and local blocked path**

```bash
uv run pytest apps/api/tests/evals/test_backup_restore.py -q
uv run python scripts/test_backup_restore.py --compose compose.yaml
test $? -eq 2
```

- [ ] **Step 5: Commit**

```bash
git add infra/backup scripts/test_backup_restore.py apps/api/tests/evals/test_backup_restore.py docs/operations/backup-and-restore.md
git commit -m "chore(backup): verify real restore evidence"
```

### Task 5: Consume immutable release inputs

**Files:**
- Modify: `scripts/verify_release.py`
- Create: `evals/reports/schema/release-input.schema.json`
- Modify: `apps/api/tests/evals/test_release_decision.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: `--stage-a`, `--stage-b`, `--stage-c`, `--outcomes`, `--incidents`, `--threshold-changes`
- Produces: release decision with per-input hashes and non-zero non-pass exit

- [ ] **Step 1: Write failing mandatory-input tests**

```python
def test_missing_mandatory_outcome_fails(release_inputs) -> None:
    del release_inputs.outcomes["OUT-001"]
    assert decide_release(release_inputs).decision == "FAIL"

def test_fail_cli_returns_nonzero(tmp_path) -> None:
    assert main(["--output", str(tmp_path / "release.json")]) == 1
```

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/evals/test_release_decision.py -q`

- [ ] **Step 3: Replace hard-coded inputs**

Load all required files, validate their status and schema version, require the complete mandatory outcome set, and compute SHA-256 over raw input bytes. `BLOCKED_EXTERNAL` in any required input yields release `FAIL` with reason `EXTERNAL_EVIDENCE_BLOCKED`.

- [ ] **Step 4: Fix conditional-pass logic**

```python
if mandatory_missing or mandatory_failed:
    return ReleaseDecision("FAIL", ("MANDATORY_OUTCOME_FAILED",))
optional_failures = [o for metric, o in outcomes.items() if metric not in MANDATORY_OUTCOMES and not o.passed]
if not optional_failures:
    return ReleaseDecision("PASS", ())
if len(optional_failures) == 1 and optional_failures[0].within_ten_percent and inputs.reevaluation_date:
    return ReleaseDecision("CONDITIONAL_PASS", ("ONE_OPTIONAL_OUTCOME_NEAR_THRESHOLD",))
return ReleaseDecision("FAIL", ("OUTCOME_GATE_FAILED",))
```

- [ ] **Step 5: Wire Make**

Add `verify-stage-a`, `verify-stage-b`, `verify-stage-c`, and `verify-release` targets. `make verify` runs local-complete gates; external-blocked gates run under `make verify-release-readiness` and must remain non-zero until supplied.

- [ ] **Step 6: Verify and commit**

```bash
uv run pytest apps/api/tests/evals/test_release_decision.py -q
make verify-stage-a
make verify-release-readiness
test $? -ne 0
git add scripts/verify_release.py evals/reports/schema/release-input.schema.json apps/api/tests/evals/test_release_decision.py Makefile
git commit -m "feat(release): fail closed on incomplete evidence"
```
