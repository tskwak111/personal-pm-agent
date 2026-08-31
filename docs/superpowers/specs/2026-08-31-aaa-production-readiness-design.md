# AAA Production Readiness Remediation Design

- **Status:** Approved scope, implementation design
- **Date:** 2026-08-31
- **Authority:** Existing normative product, planner, evaluation, state-machine, traceability, and quality documents
- **Execution boundary:** Repository-verifiable production readiness without live Google credentials, a deployed production environment, or a four-week user pilot

## 1. Goal

Make every shipped claim evidence-backed. The repository is production-ready only when core invariants hold in real execution paths, release gates fail closed, browser and deployment contracts are runnable, and documentation matches current evidence.

“AAA” does not mean adding features or abstractions. It means:

1. no known safety, authorization, ownership, scheduling, or external-action invariant violation;
2. no gate that reports success without measuring its claimed condition;
3. no UI, client, worker, or deployment artifact that is presented as functional while disconnected;
4. reproducible positive and negative verification;
5. explicit `BLOCKED_EXTERNAL` status for evidence requiring credentials, deployment, private data, or real users.

## 2. Normative precedence

This remediation does not redefine product behavior. Conflicts resolve in this order:

1. `docs/architecture/decision-precedence.md`;
2. product and planner normative specifications;
3. evaluation and pilot requirements;
4. state machines, traceability, acceptance scenarios, and Definition of Done;
5. phase plans and current implementation.

An existing “Complete” marker is not evidence. Tests and generated reports must demonstrate the condition they name.

## 3. Chosen approach

Use risk-ordered vertical remediation. Each stream fixes a complete path from input to observable result, adds the smallest regression test that proves the root cause, and updates its evidence before the next stream begins.

Rejected alternatives:

- **Phase-by-phase rewrite:** too broad, obscures root causes, and risks replacing working code.
- **Gate-only hardening:** would make reports truthful but leave production behavior unsafe.
- **Feature completion first:** would expand attack and failure surfaces before repairing stop-ship defects.

## 4. Work streams

### 4.1 Safety and planning integrity

Repair stop-ship behavior first:

- enforce `BLOCKS_START` against the predecessor’s actual completion time in every scheduling pass;
- preserve freeze-window and user-pinned allocations unless an authorized proposal is accepted;
- hydrate Planner input from persisted calendar events, task dependencies, external dependencies, prior valid plan, pins, and workspace timezone;
- never report an external action as executed or verified when no executor ran;
- preserve the last valid plan on failed planning or replanning;
- fix local-date selection and remaining model/workspace scope invariants.

The Planner remains dependency-free and deterministic. Shared scheduling functions, not callers, own dependency timing enforcement.

### 4.2 Truthful evaluation and release gates

Replace synthetic success with measured evidence:

- Stage A maps actual invariant executions to every SAFE/PLAN gate and runs the requested scenario count;
- Stage B validates dataset denominators and required metrics, reports incomplete datasets as `BLOCKED_EXTERNAL` or `FAIL`, and exits non-zero on failure;
- Stage C requires every declared metric, handles missing evidence without crashing, and derives results from fault executions;
- release verification consumes report files, rejects missing or stale mandatory inputs, preserves immutable thresholds, and exits non-zero for non-pass decisions;
- backup/restore verification performs a real isolated restore comparison or reports `BLOCKED_EXTERNAL`;
- Make and CI run these gates rather than echo-only placeholders.

Reports contain code revision, input hashes, denominators, timestamps, environment, and command outcomes.

### 4.3 API authorization, security, and external execution

Connect existing controls at trust boundaries:

- CSRF and rate limiting protect the intended request classes with deterministic window reset behavior;
- uploads pass validation and scanning before extraction;
- untrusted document content cannot create commands or outbox records;
- approval commands route through the approval service and validate actor, workspace, object version, proposal hash, state transition, audit, and execution authorization;
- OAuth callback rejects missing/invalid state or code and never marks a connection active before verified token persistence;
- readiness checks required runtime dependencies rather than returning a process-only success;
- logs redact sensitive values on the live logging path.

Unavailable providers fail closed. No simulated provider success is exposed as a production outcome.

### 4.4 Functional Web/PWA and generated API contract

Make the shipped browser flow real:

- generate typed request/response contracts and callable client functions from the canonical OpenAPI document;
- fail CI when the running application OpenAPI differs from the committed artifact;
- connect app shell, navigation, authentication actions, today/projects/inbox/calendar/approval data, mutations, error states, and loading states;
- register the service worker only where its cache and update behavior is tested;
- supply valid manifest assets or remove invalid declarations;
- make Playwright and accessibility tests mandatory, assertion-bearing, and non-conditional;
- remove echo-only package checks.

The web application may use deterministic local fixtures only in explicit test mode. Production builds must call the API or render a clear unavailable state.

### 4.5 Runtime, deployment, recovery, and observability

Make artifacts runnable and verifiable:

- declare every Python workspace dependency used by API and worker packages;
- produce the Next standalone output expected by the image, or simplify the image to the actual build output;
- validate Kubernetes selectors, labels, probes, immutable image references, migration separation, and non-root execution;
- implement a worker entry point that consumes the existing outbox/job path and reports failures accurately;
- verify database readiness, migration compatibility, backup/restore integrity, retention, and deletion evidence;
- connect privacy-safe structured logs, correlation IDs, metrics, and alerts to live application paths.

Credentialed deployment, registry digests, managed storage, and disaster-recovery timing remain external evidence and cannot be marked passed locally.

### 4.6 Documentation, traceability, and deletion

Make repository claims auditable:

- derive implementation status from completed, runnable evidence;
- reconcile phase checkboxes, risk status, decision log, package summary, and verification evidence;
- remove or repair traceability links to nonexistent evidence;
- record each RED/GREEN/regression command with revision and exit status;
- delete unused one-implementation interfaces, duplicate hooks/wrappers, and dead helpers where tests confirm no behavior is lost.

Documentation is updated with each stream, not in a final cosmetic sweep.

## 5. Data and control flow

```text
request / persisted facts
  -> ownership, version, authorization, trust-boundary validation
  -> deterministic domain or planner command
  -> transactional state + audit + outbox
  -> worker/provider execution
  -> verified external result linked by idempotency key and provider ID
  -> API/OpenAPI client
  -> Web state with explicit pending/succeeded/failed presentation
  -> telemetry and release evidence
```

No layer may skip the preceding authorization or verification boundary. Candidate LLM output enters only as untrusted structured input.

## 6. Failure semantics

- Missing mandatory inputs: `FAIL`.
- Evidence that intrinsically requires credentials, private datasets, deployment, or real users: `BLOCKED_EXTERNAL`.
- Provider absent, timed out, or unverified: external action remains pending/failed, never succeeded.
- Planning failure: retain the last valid snapshot and return explicit unresolved evidence.
- Gate process: machine-readable report plus non-zero exit on `FAIL`; `BLOCKED_EXTERNAL` is non-releaseable and also exits non-zero unless the command explicitly requests a local-only readiness profile.
- UI: show unavailable/pending/failed state and preserve retry or recovery action where safe.

## 7. Testing strategy

Every behavior change follows TDD:

1. reproduce the audited failure with the smallest deterministic test;
2. confirm the intended RED result;
3. fix the shared root cause with minimum code;
4. run focused and adjacent suites;
5. run the relevant negative gate fixture and confirm non-zero failure;
6. run the positive gate fixture and confirm success;
7. run repository verification and record exact results.

Required final local evidence:

```bash
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
git diff --check
```

Stage A runs the normative 20,000 generated scenarios. Stage B, Stage C, release, deployment, and recovery commands must either pass with complete local evidence or return a documented non-zero `BLOCKED_EXTERNAL`/failure result.

## 8. Completion contract

Repository-verifiable AAA readiness requires all of the following:

- audited Planner dependency and pin/freeze reproductions pass;
- no code path records unexecuted or unverified external success;
- persisted facts reach Planner input and authorization services;
- all local safety gates are measured, complete, schema-valid, and fail closed;
- unit, integration, browser E2E, accessibility, build, OpenAPI drift, migration, and deployment contract checks pass;
- API, worker, and web production artifacts have runnable entry points;
- status, risks, traceability, phase plans, and verification evidence agree;
- no Critical or Important review finding remains;
- every external-only item is listed with its required evidence and `BLOCKED_EXTERNAL` status.

Live Google OAuth/write success, registry-pinned deployed images, managed backup recovery objectives, Stage B private-scale corpus, and Stage D user outcomes are explicitly outside local completion. They become passable only when their real environments and data are supplied.

## 9. Execution decomposition

Implementation is split into independently reviewable plans in this order:

1. safety and planning integrity;
2. truthful evaluation and release gates;
3. API authorization and external execution;
4. Web/PWA and OpenAPI client;
5. deployment, worker, recovery, and observability;
6. documentation, traceability, and dead-code deletion;
7. whole-repository verification and final review.

Later streams may not weaken tests or thresholds established by earlier streams. Each stream must leave the repository in a buildable, reviewable state.
