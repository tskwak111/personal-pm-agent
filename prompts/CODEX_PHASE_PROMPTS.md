# Codex Phase Resume Prompts

Use the Master Meta-Prompt for a fresh repository. These concise prompts are for resuming a specific approved Phase after prior Phases are verified.

## Universal resume prefix

```text
Continue the Personal PM Agent repository under AGENTS.md and the approved specifications. Load using-superpowers first, verify the isolated worktree, run `python3 scripts/verify_package.py`, inspect `docs/status/IMPLEMENTATION_STATUS.md`, and execute the first incomplete stable Task ID in the requested Phase. Use subagent-driven-development, TDD, systematic debugging, code review and fresh verification. Do not weaken scope, authority rules, planner semantics or evaluation gates. Read the full active Phase plan before editing. Update Phase checkboxes, status, verification evidence, decisions/risks and traceability after each Task. Commit atomically.
```

## Phase 0 — Foundation

```text
[Universal resume prefix]
Execute `docs/plans/01-phase-0-foundation.md`. Establish the exact supported toolchain, monorepo, Docker Compose services, pure Planner/API/Worker/Web bootstraps, root quality command contract and clean-checkout CI. Do not implement product behavior early. Finish only when Gate G0 passes from a clean checkout.
```

## Phase 1 — Domain Core

```text
[Universal resume prefix]
Execute `docs/plans/02-phase-1-domain-core.md`. Keep all types framework-independent and immutable. Implement IDs/time, workstream/milestone/task snapshots, the exact state machine, dependency semantics, availability/calendar/external dependency snapshots, authorization and version-bound proposal/approval/audit contracts, then freeze Planner I/O. Finish only when Gate G1 has zero authority/state invariant violations.
```

## Phase 2 — Planner Engine

```text
[Universal resume prefix]
Execute `docs/plans/03-phase-2-planner-engine.md` against the entire Planner Normative Spec. Enforce explicit clock/timezone, unknown-time semantics, unique global slots, cycle rejection, normative priority tuple, split rules, independent Base/Safety passes, allocation-based risk, latest-safe handoffs, lexicographic minimal-change replanning and quantified overload proposals. Finish only when all reference vectors, determinism, performance and at least 20,000 property cases satisfy Gate G2.
```

## Phase 3 — Persistence and API

```text
[Universal resume prefix]
Execute `docs/plans/04-phase-3-persistence-api.md`. Build normalized PostgreSQL persistence behind ports and Unit of Work, ownership/session enforcement, optimistic concurrency, idempotent command envelopes, canonical application services, immutable Plan Snapshots, transactional outbox and generated TypeScript OpenAPI client. Routers contain no domain logic. Finish only when Gate G3 passes on real integration services.
```

## Phase 4 — Inbox, Files and LLM

```text
[Universal resume prefix]
Execute `docs/plans/05-phase-4-intake-llm-files.md`. Preserve raw sources and immutable extraction versions, implement safe upload/parser jobs, Inbox lifecycle, provider-independent LLM Gateway, source-linked candidates, evidence/calibration/harm policy, conflict handling and approved decomposition. External content remains untrusted and tool-less. Finish only when Gate G4 and Stage B structure/source safety thresholds pass.
```

## Phase 5 — Calendar and Execution

```text
[Universal resume prefix]
Execute `docs/plans/06-phase-5-calendar-execution.md`. Use incremental OAuth, encrypted token vault, recurrence/exception/tombstone/timezone/field-ownership sync, version-bound focus-block approval, transactional outbox, idempotent verified execution, retry/reauthorization/dead-letter classification and webhook plus periodic reconciliation. Finish only when Gate G5 and Stage C fault injection prove zero duplicate and zero false-success behavior.
```

## Phase 6 — Agent, Approval and Briefing

```text
[Universal resume prefix]
Execute `docs/plans/07-phase-6-agent-briefing.md`. Persist typed Agent Operations, distinguish ambiguous questions from commands, build least-context retrieval, execute the explicit Observe→Interpret→Retrieve→Plan→Critique→Authorize→Act→Verify→Explain→Learn flow, complete approval/undo, Work Sessions, analytics, evidence-grounded briefings and deduplicated notifications/SSE. Finish only when Gate G6 proves authority and truthfulness.
```

## Phase 7 — Web/PWA

```text
[Universal resume prefix]
Execute `docs/plans/08-phase-7-web-pwa.md`. Implement the approved accessible responsive UX using only generated API types: Life Audit onboarding, Today, Inbox, Projects, Calendar, Review/Approval and resumable Agent panel, then opt-in PWA/Web Push and critical E2E/interaction instrumentation. Do not add unapproved dashboard or optimistic external success. Finish only when Gate G7 and UX/accessibility gates pass.
```

## Phase 8 — Evaluation and Release

```text
[Universal resume prefix]
Execute `docs/plans/09-phase-8-evaluation-security-deployment.md`. Version telemetry, automate Stage A–C reports, harden auth/files/logging/prompt boundaries, add tracing/metrics/SLOs, production containers, backup/restore/deletion proof, controlled pilot tooling and an immutable final release decision. Any Hard Gate violation forces Fail; do not lower thresholds. Finish only when P8-T10 independently verifies all evidence and hashes.
```
