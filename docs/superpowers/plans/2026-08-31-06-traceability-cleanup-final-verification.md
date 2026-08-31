# Traceability, Cleanup, and Final Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make documentation mechanically truthful, delete verified dead code, and finish with reproducible whole-repository evidence.

**Architecture:** Repository verification checks evidence links and status consistency as code. Cleanup removes only symbols proven unused; the final gate distinguishes local PASS from external `BLOCKED_EXTERNAL`.

**Tech Stack:** Python 3.13 stdlib, rg, Git, Make, pytest, Playwright

**Spec:** `docs/superpowers/specs/2026-08-31-aaa-production-readiness-design.md`

## Global Constraints

- Documentation never claims a command, test count, deployment, dataset, or pilot result that was not observed.
- Missing evidence paths fail repository verification.
- External credentials, private corpora, production infrastructure, security advisory services, and real users stay `BLOCKED_EXTERNAL`.
- Deletion requires zero non-definition callers plus passing affected tests.
- Completion requires no Critical or Important review finding.

---

### Task 1: Enforce traceability evidence integrity

**Files:**
- Modify: `scripts/verify_repo.py`
- Create: `tests/handoff/test_traceability_contract.py`
- Modify: `docs/requirements/requirements-traceability.md`
- Modify: `docs/quality/verification-command-matrix.md`

**Interfaces:**
- Produces: repository verifier failure for nonexistent local evidence paths, unknown test nodes, or unsupported completion claims

- [x] **Step 1: Write a failing missing-reference test**

```python
def test_traceability_rejects_missing_local_evidence(tmp_path: Path) -> None:
    doc = tmp_path / "traceability.md"
    doc.write_text("| R-1 | Implemented | tests/missing_test.py |\n")
    errors = verify_traceability(doc, repo_root=tmp_path)
    assert errors == ["R-1: missing evidence path tests/missing_test.py"]
```

Add tests for a valid `path::test_name`, an external `BLOCKED_EXTERNAL` record, and a line that says Complete with no evidence.

- [x] **Step 2: Confirm RED**

Run: `uv run pytest tests/handoff/test_traceability_contract.py -q`

- [x] **Step 3: Parse local references conservatively**

Use `pathlib.Path` and regular expressions from stdlib. Accept repository-relative paths and optional `::pytest_node`; reject paths outside the repository. For pytest nodes, verify the file contains the named function or class method. Do not validate URLs or external ticket IDs as local files.

- [x] **Step 4: Repair every broken reference**

For each missing path, either point to the real implementation/test/report, change status to `Not Implemented`, or mark `BLOCKED_EXTERNAL` with the exact required evidence. Do not create empty evidence files.

- [x] **Step 5: Verify and commit**

```bash
uv run pytest tests/handoff/test_traceability_contract.py -q
python3 scripts/verify_repo.py
git add scripts/verify_repo.py tests/handoff/test_traceability_contract.py docs/requirements/requirements-traceability.md docs/quality/verification-command-matrix.md
git commit -m "test(docs): enforce traceability evidence links"
```

### Task 2: Reconcile status, plans, decisions, and risks

**Files:**
- Modify: `docs/status/IMPLEMENTATION_STATUS.md`
- Modify: `docs/status/DECISION_LOG.md`
- Modify: `docs/status/RISK_REGISTER.md`
- Modify: `docs/status/VERIFICATION_EVIDENCE.md`
- Modify: `docs/status/HANDOFF_CHECKLIST.md`
- Modify: `docs/plans/00-master-implementation-roadmap.md`
- Modify: `docs/plans/03-phase-2-planner-engine.md`
- Modify: `docs/plans/04-phase-3-persistence-api.md`
- Modify: `docs/plans/08-phase-7-web-pwa.md`
- Modify: `docs/plans/09-phase-8-evaluation-security-deployment.md`
- Modify: `PACKAGE_SUMMARY.md`

**Interfaces:**
- Produces: one consistent local-readiness status and one external-evidence table

- [x] **Step 1: Add a status-consistency contract**

```python
def test_complete_phase_has_checked_exit_criteria_or_external_block() -> None:
    errors = verify_phase_status(REPO_ROOT)
    assert errors == []
```

The verifier rejects `Complete` when a phase exit criterion is unchecked without `BLOCKED_EXTERNAL`.

- [x] **Step 2: Confirm RED**

Run: `uv run pytest tests/handoff/test_traceability_contract.py -q`

- [x] **Step 3: Reconcile claims from evidence**

Use these exact top-level states:

- `Local Production Readiness: PASS` only after final local commands pass;
- `Release: BLOCKED_EXTERNAL` while Stage B private corpus, Stage C live provider, deployed digests/rollout, backup RPO/RTO, advisory audits, or Stage D outcomes are absent.

Check phase items backed by real files/tests. Leave external items unchecked and annotate their required evidence.

- [x] **Step 4: Record decisions and risks**

Record the local/external split, bearer-only CSRF decision, digest-rendering decision, and in-process metric ceiling. Reopen any risk previously marked mitigated by a synthetic runner.

- [x] **Step 5: Verify and commit**

```bash
python3 scripts/verify_package.py
python3 scripts/verify_repo.py
uv run pytest tests/handoff -q
git add docs PACKAGE_SUMMARY.md
git commit -m "docs(status): reconcile readiness with evidence"
```

### Task 3: Delete only proven dead code

**Files:**
- Delete if unused: `apps/api/src/personal_pm_api/shared/unit_of_work.py`
- Modify: `apps/worker/src/personal_pm_worker/calendar/executor.py`
- Delete if unused: `apps/web/src/features/onboarding/use-onboarding.ts`
- Modify: `apps/api/src/personal_pm_api/analytics/pilot.py`
- Modify: `apps/api/src/personal_pm_api/identity/router.py`
- Modify: `apps/api/src/personal_pm_api/telemetry/events.py`
- Modify: `apps/api/src/personal_pm_api/execution/outbox.py`
- Modify: `apps/api/src/personal_pm_api/calendar/focus_blocks.py`
- Modify: `scripts/run_stage_c.py`

**Interfaces:**
- Produces: unchanged public behavior with fewer unused symbols

- [ ] **Step 1: Prove each candidate unused**

```bash
rg -n 'UnitOfWork|uow_context' --glob '!apps/api/src/personal_pm_api/shared/unit_of_work.py'
rg -n 'useOnboarding' --glob '!apps/web/src/features/onboarding/use-onboarding.ts'
rg -n 'ActorDependency|_base\(|utc_now\(|LatencyLike|_load_proposal'
```

For each symbol, retain it if a production caller exists. Protocols with multiple concrete test/production implementations stay.

- [ ] **Step 2: Run affected tests before deletion**

```bash
uv run pytest apps/api/tests/integration/test_unit_of_work.py apps/api/tests/integration/test_pilot_metrics.py apps/api/tests/integration/test_focus_block_approval.py apps/worker/tests/calendar -q
pnpm --filter @personal-pm/web test --run src/test/onboarding.test.tsx
```

- [ ] **Step 3: Delete wrappers, not behavior**

Inline a wrapper only when the callee is already the sole public behavior. Delete unused helpers and imports. Do not collapse ownership, transaction, executor, parser, storage, or Planner structural protocols that have multiple implementations.

- [ ] **Step 4: Verify and commit**

```bash
make format-check
make lint
make typecheck
make test-unit
git diff --check
git add -A
git commit -m "refactor(repo): delete verified dead code"
```

### Task 4: Run whole-repository negative and positive verification

**Files:**
- Modify: `docs/status/VERIFICATION_EVIDENCE.md`
- Create: `evals/reports/local-production-readiness.json`

**Interfaces:**
- Produces: immutable local readiness report with command, exit code, counts, revision, and input hashes

- [ ] **Step 1: Verify failure paths**

Run fixtures that intentionally violate:

- PLAN-002 dependency ordering;
- pin/freeze preservation;
- missing external executor;
- omitted Stage A gate;
- incomplete Stage B corpus;
- missing Stage C metric;
- missing mandatory release outcome;
- invalid deployment digest;
- missing traceability path.

Assert every corresponding command exits non-zero and emits the expected reason code.

- [ ] **Step 2: Run fresh positive commands**

```bash
make bootstrap
make format-check
make lint
make typecheck
make test-unit
make test-integration
make test-e2e
make build
make verify
python3 scripts/verify_package.py
python3 scripts/verify_repo.py
uv run python scripts/run_stage_a.py --scenarios 20000 --output /tmp/pma-stage-a-final.json
git diff --check
```

Record exact exit codes and failure counts. Do not reuse prior output files.

- [ ] **Step 3: Create the local report**

The JSON report contains:

```python
payload = {
    "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "profile": "local-production-readiness",
    "decision": "PASS" if all(command.exit_code == 0 for command in commands) else "FAIL",
    "commands": [asdict(command) for command in commands],
    "external_blockers": external_blockers,
}
```

Populate values from the fresh run. `decision` remains FAIL until every mandatory local command is zero.

- [ ] **Step 4: Commit evidence**

```bash
git add evals/reports/local-production-readiness.json docs/status/VERIFICATION_EVIDENCE.md
git commit -m "test(release): record local production readiness"
```

### Task 5: Independent final review and finish

**Files:**
- Review: all changes from `5993152` to HEAD

- [ ] **Step 1: Invoke `superpowers:requesting-code-review`**

Request a whole-branch review against the approved spec, normative documents, and all six plans. Reviewer reports only Critical, Important, Minor, strengths, and READY/NOT READY with file:line evidence.

- [ ] **Step 2: Fix Critical and Important findings with TDD**

Each finding gets one reproduction, root-cause fix, focused verification, and scoped re-review. Do not bundle unrelated refactoring.

- [ ] **Step 3: Invoke `superpowers:verification-before-completion`**

Repeat every final command after the last fix. A previous green run does not count.

- [ ] **Step 4: Reconcile final status**

Set local readiness PASS only if the final review is READY and all local commands are green. Keep release `BLOCKED_EXTERNAL` until the explicit external evidence table is empty.

- [ ] **Step 5: Invoke `superpowers:finishing-a-development-branch`**

Present merge/PR/keep-worktree options. Do not push, merge, publish, or delete the worktree without the user's choice.
