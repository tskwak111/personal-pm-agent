# Personal PM Agent Master Implementation Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved Personal PM Agent as a secure, deterministic, testable Web/PWA with Planning Core, LLM-assisted intake, Google Calendar execution, measurable quality gates and pilot tooling.

**Architecture:** A pnpm and uv monorepo contains a Next.js Web/PWA, FastAPI modular monolith, separate worker and pure Python Planner package. PostgreSQL is the system of record; Redis supports jobs, locks and rate limits; object storage preserves source files; all external writes pass through approval, transactional outbox, idempotency and verification.

**Tech Stack:** Python 3.13, FastAPI 0.141.x, SQLAlchemy 2.x, PostgreSQL 18, Redis 8, Next.js 16, React 19.2, TypeScript, pnpm, uv, pytest, Hypothesis, Vitest, Playwright, Docker Compose.

**Spec:** `docs/specs/2026-08-23-personal-pm-agent-design.md`, `docs/specs/2026-08-23-personal-pm-agent-planner-normative-spec.md`, `docs/specs/2026-08-23-personal-pm-agent-evaluation-and-pilot-plan.md`

## Global Constraints

- Product and UX behavior must follow the approved design spec.
- Planner behavior must follow Planner Spec v1.0 exactly and remain independent of LLM, network and database SDKs.
- Evaluation thresholds must not be weakened to accommodate current implementation results.
- Every state-changing command must verify workspace ownership and expected object version.
- Hard Deadline, Fixed Event, external message and irreversible action policies must be enforced in code, not prompts.
- External writes require outbox, idempotency, external result verification and explicit internal/external status.
- TDD, strict typing, atomic commits and fresh completion verification are mandatory.

---

## 1. Phase Dependency Graph

```text
Phase 0 Foundation
   ↓
Phase 1 Domain Core
   ↓
Phase 2 Planner Engine ───────────────┐
   ↓                                  │
Phase 3 Persistence & API             │
   ↓                                  │
Phase 4 Intake, Files & LLM            │
   ↓                                  │
Phase 5 Calendar & External Execution │
   ↓                                  │
Phase 6 Agent, Approval & Briefing ◀───┘
   ↓
Phase 7 Web/PWA
   ↓
Phase 8 Evaluation, Security, Deployment & Pilot
```

Phase 2 can be developed in parallel with selected Phase 3 infrastructure after Phase 1 contracts are stable. No other Phase may consume an interface that has not been committed and contract-tested.

## 2. Phase Overview

| Phase | Plan | Primary deliverable | Exit gate |
|---|---|---|---|
| 0 | `01-phase-0-foundation.md` | Reproducible monorepo, local services, CI, common commands | clean checkout `make verify` |
| 1 | `02-phase-1-domain-core.md` | Immutable Planning snapshots, state machine, dependency and permission contracts | domain tests and contract fixtures pass |
| 2 | `03-phase-2-planner-engine.md` | Deterministic Base/Safety scheduler, risks, today plan, minimal-change replanning | TV-01~11 100%, invariant violations 0 |
| 3 | `04-phase-3-persistence-api.md` | PostgreSQL schema, UoW, ownership, auth, API, plan snapshots, outbox | API integration and concurrency tests pass |
| 4 | `05-phase-4-intake-llm-files.md` | Source preservation, inbox, parsing, LLM gateway, evidence and decomposition | schema/source/ambiguity contract tests pass |
| 5 | `06-phase-5-calendar-execution.md` | Google OAuth, sync, focus blocks, worker, retries and verification | Stage C fault gates pass |
| 6 | `07-phase-6-agent-briefing.md` | Orchestrator, operations, approval, sessions, briefings, notifications, SSE | authority and full operation flow tests pass |
| 7 | `08-phase-7-web-pwa.md` | Onboarding and five-screen responsive Web/PWA | critical flows, accessibility and browser E2E pass |
| 8 | `09-phase-8-evaluation-security-deployment.md` | Metric automation, hardening, deploy, backup and pilot tooling | Stage A~C report is reproducible |

## 3. Cross-Phase Interfaces

### Planner package

```python
from personal_pm_planner import PlannerInput, PlannerOutput, plan

output: PlannerOutput = plan(input_snapshot)
```

The same canonical input and `planner_version` must return the same normalized core output.

### Application planning service

```python
class PlanningService(Protocol):
    async def create_plan(
        self,
        workspace_id: UUID,
        request: CreatePlanRequest,
    ) -> PlanSnapshotDTO: ...
```

The application service loads verified snapshots, calls the pure Planner, persists a new immutable Plan Snapshot and never overwrites the last valid plan on failure.

### LLM gateway

```python
class LLMGateway(Protocol):
    async def generate_structured(
        self,
        request: StructuredLLMRequest[T],
    ) -> StructuredLLMResult[T]: ...
```

The result is a candidate and cannot mutate Planning Core directly.

### External execution

```python
class ExternalExecutor(Protocol):
    async def execute(self, command: ExternalCommand) -> ExternalExecutionResult: ...
```

Commands are read from committed outbox records and must be idempotent.

### Web API client

The TypeScript client is generated from FastAPI OpenAPI. Hand-written duplicate domain DTOs are prohibited.

## 4. Quality Gates by Milestone

### Gate G0 — Engineering baseline

- Toolchain versions are pinned.
- Lockfiles and container digests are committed.
- `make verify` runs in local and CI environments.
- No secret values exist in repository history.

### Gate G1 — Domain safety

- State transitions, permission levels and dependency cycles have explicit tests.
- Date-only deadlines cannot contain fabricated time facts.
- Facts, inferences, proposals and executions are distinct types.

### Gate G2 — Planner conformance

- TV-01 through TV-11 pass.
- Same input repeated 100 times produces identical canonical output.
- No slot overlap, dependency violation, fixed-event collision or capacity overrun.
- Property suite is ready to scale to the required 20,000 scenarios.

### Gate G3 — State and API integrity

- Workspace isolation is enforced on every repository and command.
- Optimistic locking rejects stale commands.
- Plan Snapshot persistence is append-only.
- Outbox and state change share one database transaction.

### Gate G4 — AI intake safety

- Untrusted source content is segregated from system and user instructions.
- Every auto-registered deadline or event has source evidence.
- Missing time remains unknown.
- LLM self-confidence is not the sole automation criterion.

### Gate G5 — External execution safety

- Duplicate idempotency keys never create duplicate events.
- External failure cannot be represented as success.
- OAuth expiration produces reauthorization state.
- Recurrence exceptions, deletion tombstones and timezones have tests.

### Gate G6 — Agent authority

- Orchestrator operations are explicit state machines.
- Approval is bound to proposal and target object versions.
- Briefings use verified Planning/DecisionEvidence only.
- Notification deduplication and quiet-hour rules are deterministic.

### Gate G7 — User experience

- Core actions satisfy interaction-count requirements.
- Desktop and mobile layouts expose the same official state.
- Accessibility violations on critical screens are zero.
- Browser tests cover onboarding, task execution, replanning and approval.

### Gate G8 — Release evidence

- Stage A, B and C reports are generated from versioned inputs.
- Required security, load, backup and restore tests pass.
- Pilot consent, baseline, survey and incident workflows are operational.

## 5. Working Method

For every Task:

1. Read its `Files`, `Interfaces` and linked requirements.
2. Write the smallest failing test.
3. Run only that test and confirm the intended failure.
4. Implement the minimum behavior.
5. Run focused and adjacent regression tests.
6. Run type and lint checks for the touched language.
7. Update the Phase checkbox and status record.
8. Commit with the exact scope.
9. Review the diff before proceeding.

## 6. Branch and Commit Convention

```text
phase/00-foundation
phase/01-domain-core
phase/02-planner-engine
phase/03-persistence-api
phase/04-intake-llm
phase/05-calendar-execution
phase/06-agent-briefing
phase/07-web-pwa
phase/08-evaluation-release
```

Commit examples:

```text
chore(repo): establish reproducible workspace
feat(domain): add task state transition policy
feat(planner): allocate unique availability slots
feat(calendar): execute focus blocks idempotently
test(evals): enforce planner reference vectors
```

## 7. Phase Completion Review

Before merging a Phase branch:

- [ ] Every Phase Task checkbox is checked.
- [ ] The exact Phase verification commands pass from a clean checkout.
- [ ] New public interfaces match downstream plans.
- [ ] Migrations upgrade a blank and previous database state.
- [ ] No unreviewed placeholder or skipped test remains.
- [ ] Status, Decision Log, Risk Register and traceability are current.
- [ ] A code review uses `prompts/CODE_REVIEW_PROMPT.md`.
- [ ] Completion evidence is recorded using the Task Completion template.

## 8. Product Completion

The implementation is not release-ready until the evaluation spec returns Pass or valid Conditional Pass. Feature completion cannot substitute for safety, planning, external execution and user outcome evidence.
