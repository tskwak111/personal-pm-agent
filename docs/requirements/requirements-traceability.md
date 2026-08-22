# Requirements Traceability Matrix

This matrix connects approved behavior to implementation Tasks and planned evidence. A Task may refine paths during implementation only when the new path is recorded here and preserves the requirement.

| Requirement ID | Normative requirement | Source | Implementing Tasks | Planned verification evidence |
|---|---|---|---|---|
| REQ-PRD-001 | Planning Core is the sole canonical state for projects, tasks, deadlines, approvals and plans. | Design §5.1 | P1-T02, P3-T02, P3-T07 | packages/planner/tests/unit/test_canonical_snapshots.py; apps/api/tests/integration/test_plan_snapshot_persistence.py |
| REQ-PRD-002 | The user may capture unstructured text without first selecting a project or task type. | Design §6, §9 | P4-T03, P6-T02, P7-T08 | apps/api/tests/integration/test_freeform_capture.py; apps/web/e2e/agent-capture.spec.ts |
| REQ-PRD-003 | The system shows one core result, mandatory tasks, next queue, optional work, excluded work and required decisions for Today. | Design §12.5, §16.1 | P2-T09, P7-T03 | packages/planner/tests/reference/test_today_output.py; apps/web/e2e/today-plan.spec.ts |
| REQ-PRD-004 | Overload handling proposes removal, deferral, scope reduction and external negotiation before extra labor. | Design §13.6 | P2-T09, P6-T05, P7-T07 | packages/planner/tests/unit/test_overload_proposals.py; apps/web/e2e/overload-approval.spec.ts |
| REQ-PRD-005 | Replanning minimizes changes and protects in-progress, pinned and frozen-horizon work. | Design §12.6; Planner Spec | P2-T09 | packages/planner/tests/reference/test_minimal_change.py |
| REQ-PRD-006 | Team-member work is represented as an external dependency, not as controllable member tasks. | Design §3.2, §8.8 | P1-T05, P2-T08, P7-T05 | packages/planner/tests/unit/test_external_dependency.py |
| REQ-PRD-007 | Progress percentage and deadline feasibility are distinct outputs. | Design §8.10 | P1-T02, P2-T08, P7-T05 | packages/planner/tests/unit/test_progress_vs_feasibility.py |
| REQ-PRD-008 | The system never evaluates the user with moralizing productivity language. | Design §17.3 | P6-T07, P7-T03 | apps/api/tests/unit/test_briefing_copy_policy.py; apps/web/tests/copy-policy.test.ts |
| REQ-PRD-009 | Every automatic change exposes reason, rule/authority basis, plan version and undo status. | Design §5.7, §16.6 | P1-T06, P3-T06, P6-T05, P7-T07 | apps/api/tests/integration/test_explainable_change.py; apps/web/e2e/undo-change.spec.ts |
| REQ-PRD-010 | Onboarding can start with conversation only and optionally import calendar and files. | Design §6.2 | P4-T01, P5-T02, P7-T02 | apps/web/e2e/life-audit-onboarding.spec.ts |
| REQ-PRD-011 | Morning, evening and weekly briefings are evidence-grounded views of canonical state. | Design §6.3–§6.4 | P6-T07, P7-T03, P7-T07 | apps/api/tests/integration/test_briefings.py; apps/web/e2e/weekly-review.spec.ts |
| REQ-PRD-012 | Flexible tasks are not automatically converted into calendar events. | Design §11.1 | P5-T04, P7-T06 | apps/api/tests/integration/test_focus_block_requires_proposal.py |
| REQ-PRD-013 | Partial completion preserves finished scope and re-estimates only remaining scope. | Design §14.3 | P6-T06, P2-T09, P7-T03 | apps/api/tests/integration/test_partial_completion.py |
| REQ-PRD-014 | Blocked and Waiting are distinct states with distinct recovery predicates. | Design §14.4 | P1-T03, P7-T03 | packages/planner/tests/unit/test_task_state_machine.py |
| REQ-PRD-015 | Normal-day notification output is deduplicated, validity-checked and bounded by policy. | Design §17 | P6-T08, P7-T09 | apps/api/tests/unit/test_notification_policy.py |
| REQ-CORE-001 | All canonical IDs are typed and workspace-scoped. | Design §8; Architecture contract | P1-T01, P3-T04 | packages/planner/tests/unit/test_identifiers.py; apps/api/tests/security/test_workspace_scope.py |
| REQ-CORE-002 | All stored instants are UTC while original expression and user timezone are preserved. | Design §11; Planner Spec §date rules | P1-T01, P2-T02, P3-T02 | packages/planner/tests/unit/test_time_primitives.py |
| REQ-CORE-003 | A date-only deadline retains time_known=false and no invented time. | Planner Spec; PLAN-008 | P2-T02, P4-T05 | packages/planner/tests/reference/test_date_only_deadline.py |
| REQ-CORE-004 | Task transitions follow the explicit state machine and emit audit events. | Design §8.6; Domain state machines | P1-T03, P3-T06 | packages/planner/tests/unit/test_task_state_machine.py; apps/api/tests/integration/test_task_audit.py |
| REQ-CORE-005 | Dependency types Blocks Start, Blocks Completion, Waiting External and Related remain semantically distinct. | Design §8.9 | P1-T04, P2-T04 | packages/planner/tests/unit/test_dependency_semantics.py |
| REQ-CORE-006 | Dependency cycles are unresolved input and cannot be scheduled. | Planner Spec; PLAN-007 | P1-T04, P2-T04 | packages/planner/tests/reference/test_dependency_cycle.py |
| REQ-CORE-007 | Task duration stores base and safety estimates rather than claiming an aggregate statistical percentile. | Planner Spec estimate terminology | P1-T03, P2-T02 | packages/planner/tests/unit/test_duration_derivation.py |
| REQ-CORE-008 | Scope re-baselining is explicit and historical progress remains immutable. | Design progress model | P1-T02, P3-T06 | apps/api/tests/integration/test_scope_rebaseline.py |
| REQ-CORE-009 | Proposal approvals bind exact command hash and target versions. | Design §7.5 | P1-T06, P3-T05, P6-T05 | apps/api/tests/integration/test_version_bound_approval.py |
| REQ-CORE-010 | Changed target state invalidates prior approval. | Design §7.5 | P3-T05, P6-T05 | apps/api/tests/integration/test_stale_approval_rejected.py |
| REQ-CORE-011 | High-impact action class cannot be lowered by model output or prompt text. | Design §7; SAFE gates | P1-T06, P6-T04 | packages/planner/tests/unit/test_authority_policy.py |
| REQ-CORE-012 | Plan Snapshots are immutable and include input/rule/output digests. | Design §19.4 | P1-T07, P3-T07 | apps/api/tests/integration/test_plan_snapshot_immutability.py |
| REQ-CORE-013 | A failed candidate plan never replaces the last validated current plan. | Design §24.2; PLAN-009 | P2-T10, P3-T07 | apps/api/tests/integration/test_failed_replan_preserves_current.py |
| REQ-CORE-014 | Every canonical mutation verifies expected object version. | Design §19.3 | P3-T05, P3-T06 | apps/api/tests/integration/test_optimistic_concurrency.py |
| REQ-CORE-015 | Every canonical mutation records actor, before/after, reason, authority basis and trace ID. | Design §19.5 | P1-T06, P3-T06 | apps/api/tests/integration/test_audit_event_contract.py |
| REQ-PLN-001 | Planner is a pure deterministic package with no FastAPI, ORM, Redis, network or LLM dependency. | Design §5.3; Planner Spec | P0-T03, P2-T10 | tests/handoff/test_planner_import_boundaries.py |
| REQ-PLN-002 | Planner receives now, timezone and policy as input and never reads wall-clock time internally. | Planner Spec input contract | P1-T07, P2-T01 | packages/planner/tests/unit/test_explicit_clock.py |
| REQ-PLN-003 | Availability normalization creates unique slots and reserves fixed busy, transition and protected buffer capacity. | Planner Spec slot model | P2-T03 | packages/planner/tests/reference/test_slot_normalization.py |
| REQ-PLN-004 | Within one pass each slot has at most one task owner. | Planner Spec; PLAN-001 | P2-T03, P2-T06 | packages/planner/tests/property/test_slot_single_owner.py |
| REQ-PLN-005 | Global scheduling prevents two deadlines from independently consuming the same capacity. | Planner Spec global allocation | P2-T06, P2-T07 | packages/planner/tests/reference/test_shared_capacity.py |
| REQ-PLN-006 | Base and Safety passes are independent allocations over the same normalized capacity. | Planner Spec pass model | P2-T07 | packages/planner/tests/reference/test_base_safety_independence.py |
| REQ-PLN-007 | Safety pass includes validation, submission and uncertainty buffers as synthetic work. | Planner Spec buffer rules | P2-T07 | packages/planner/tests/unit/test_synthetic_buffers.py |
| REQ-PLN-008 | Priority class precedes scoring and uses the normative stable tie-break tuple. | Planner Spec priority tuple | P2-T05 | packages/planner/tests/reference/test_priority_ties.py |
| REQ-PLN-009 | Split and non-split tasks obey minimum chunk and contiguity rules. | Planner Spec scheduling | P2-T06 | packages/planner/tests/reference/test_split_non_split.py |
| REQ-PLN-010 | Blocks Start and Blocks Completion constrain different schedule points. | Planner Spec dependencies | P2-T04, P2-T06 | packages/planner/tests/reference/test_dependency_timing.py |
| REQ-PLN-011 | External dependency risk uses latest_safe_handoff_at, expected delivery, fallback and recovery time. | Planner Spec external dependency risk | P2-T04, P2-T08 | packages/planner/tests/reference/test_latest_safe_handoff.py |
| REQ-PLN-012 | Critical risk is based on allocated feasibility, not only due-date distance. | Planner Spec risk rules | P2-T08 | packages/planner/tests/reference/test_risk_from_allocation.py |
| REQ-PLN-013 | Unknown inputs yield Unknown/unresolved outcomes rather than Low risk. | Design §13.4 | P2-T01, P2-T08 | packages/planner/tests/reference/test_unknown_risk.py |
| REQ-PLN-014 | Today plan limits high-focus workstreams and reports explicit excluded work. | Design §12.5 | P2-T09 | packages/planner/tests/reference/test_today_workstream_limit.py |
| REQ-PLN-015 | Replanning uses lexicographic safety/feasibility objectives before change minimization. | Planner Spec replanning objective | P2-T09 | packages/planner/tests/reference/test_lexicographic_replan.py |
| REQ-PLN-016 | In-progress, user-pinned and frozen-horizon items cannot move without the defined exception. | Planner Spec frozen rules | P2-T09 | packages/planner/tests/property/test_frozen_items.py |
| REQ-PLN-017 | Overload proposals include quantified capacity effect and authority class. | Planner Spec overload output | P2-T09 | packages/planner/tests/unit/test_overload_effects.py |
| REQ-PLN-018 | All Planner decisions emit stable Rule IDs and source evidence. | Planner Spec explanations | P1-T07, P2-T10 | packages/planner/tests/unit/test_decision_evidence.py |
| REQ-PLN-019 | All normative reference vectors pass exactly and are version-controlled. | Planner Spec §19; PQ-001 | P2-T10, P8-T02 | packages/planner/tests/reference/ |
| REQ-PLN-020 | At least 20,000 generated scenarios pass planner invariants before release. | Evaluation Stage A | P2-T10, P8-T02 | reports/stage-a/planner-property-report.json |
| REQ-AI-001 | Raw source bytes, extraction text, structured candidates and canonical records are separate objects. | Design §9.4, §20 | P4-T01, P4-T02, P4-T03 | apps/api/tests/integration/test_source_separation.py |
| REQ-AI-002 | Every extracted fact/candidate links to source artifact and location. | Design §9.3; AI-003 | P4-T05 | apps/api/tests/golden/test_source_references.py |
| REQ-AI-003 | LLM calls pass through a provider-independent gateway with model, prompt and schema versions. | Design §22.1 | P4-T04 | apps/api/tests/unit/test_llm_gateway.py |
| REQ-AI-004 | Structured outputs are schema-validated before application policy sees them. | Design §22.3 | P4-T04 | apps/api/tests/unit/test_structured_output_validation.py |
| REQ-AI-005 | Document content is always untrusted and cannot select a tool or authority. | Design §20, §22.4; SAFE-006 | P4-T02, P4-T04, P8-T05 | apps/api/tests/security/test_document_prompt_injection.py |
| REQ-AI-006 | Evidence score, calibrated probability, model confidence and expected harm are separate values. | Planner/evaluation correction | P4-T05, P4-T06 | apps/api/tests/unit/test_evidence_and_harm_policy.py |
| REQ-AI-007 | Auto-registration requires calibrated evidence and low expected harm; high-impact ambiguity requires confirmation. | Design §9.3 | P4-T06 | apps/api/tests/integration/test_auto_registration_policy.py |
| REQ-AI-008 | Conflicting deadline sources cannot be automatically resolved. | Design §9.3, §24.5; AI-014 | P4-T06, P7-T04 | apps/api/tests/golden/test_conflict_confirmation.py |
| REQ-AI-009 | Project decomposition produces executable chunks, dependencies, completion conditions and uncertainty. | Design §10 | P4-T07 | apps/api/tests/golden/test_project_decomposition.py |
| REQ-AI-010 | Golden evaluation is split to protect an unseen test partition from prompt tuning. | Evaluation Stage B | P4-T08, P8-T03 | evaluation/manifests/golden-split.json; reports/stage-b/ |
| REQ-CAL-001 | Calendar read and write consent are requested incrementally with least privilege. | Design §25.1 | P5-T01 | apps/api/tests/security/test_incremental_scopes.py |
| REQ-CAL-002 | OAuth tokens are encrypted, redacted and revocable. | Design §25.2 | P5-T01, P8-T05 | apps/api/tests/security/test_token_vault.py |
| REQ-CAL-003 | Imported events preserve provider calendar ID, event ID, version, timezone and sync status. | Design §23.2 | P5-T02 | apps/api/tests/integration/test_calendar_import.py |
| REQ-CAL-004 | Recurrence exceptions, tombstones, all-day semantics and field ownership are explicit. | Calendar contract | P5-T03 | apps/api/tests/integration/test_calendar_recurrence_and_tombstones.py |
| REQ-CAL-005 | A focus block write requires a version-bound proposal and approval. | Design §7.3, §23 | P5-T04 | apps/api/tests/integration/test_focus_block_approval.py |
| REQ-CAL-006 | Internal change and outbox event commit atomically. | Design §21.4 | P3-T08, P5-T05 | apps/api/tests/integration/test_transactional_outbox.py |
| REQ-CAL-007 | External execution uses an idempotency key and does not duplicate provider objects. | Design §21.3; EXT-002 | P5-T05, P5-T08 | apps/worker/tests/fault/test_duplicate_delivery.py |
| REQ-CAL-008 | External success is shown only after provider result verification and external identity linkage. | Design §23.4; SAFE-004 | P5-T05 | apps/worker/tests/integration/test_verified_success.py |
| REQ-CAL-009 | Retryable, permanent, reauthorization and dead-letter failures remain distinct. | Design §24.4 | P5-T06 | apps/worker/tests/unit/test_execution_failure_classification.py |
| REQ-CAL-010 | Webhook gaps are repaired by periodic reconciliation without forced restoration of user edits. | Design §23.3; EXT-005 | P5-T07 | apps/worker/tests/integration/test_calendar_reconciliation.py |
| REQ-UX-001 | Desktop and mobile use the approved five-area information architecture plus global agent panel. | Design §16 | P7-T01 | apps/web/e2e/navigation.spec.ts |
| REQ-UX-002 | Today view allows start, complete, partial, blocked and replan actions with minimal interaction. | Design §16.1; UX metrics | P7-T03 | apps/web/e2e/today-actions.spec.ts |
| REQ-UX-003 | Inbox shows raw source beside interpretation, uncertainty and confirmation controls. | Design §16.2 | P7-T04 | apps/web/e2e/inbox-review.spec.ts |
| REQ-UX-004 | Project view separates progress, feasibility, bottleneck and external waiting. | Design §16.3 | P7-T05 | apps/web/e2e/project-health.spec.ts |
| REQ-UX-005 | Calendar shows fixed events, focus blocks, flexible queue and internal/external sync state distinctly. | Design §16.4 | P7-T06 | apps/web/e2e/calendar-truth.spec.ts |
| REQ-UX-006 | Review and Approval Center exposes before/after, impact, reason and exact action. | Design §16.5–§16.6 | P7-T07 | apps/web/e2e/approval-center.spec.ts |
| REQ-UX-007 | Agent operation streaming is resumable and cannot imply execution before verification. | Design Agent loop | P6-T08, P7-T08 | apps/web/e2e/agent-operation-stream.spec.ts |
| REQ-UX-008 | PWA offline behavior is read-safe and does not queue dangerous writes without explicit design. | Design Web/PWA | P7-T09 | apps/web/e2e/pwa-offline.spec.ts |
| REQ-UX-009 | Critical journeys meet keyboard, semantic and automated accessibility gates. | Evaluation UX | P7-T10 | reports/web/accessibility.json |
| REQ-UX-010 | Interaction telemetry measures the defined UX completion thresholds without recording private content. | Evaluation UX-001–006 | P7-T10, P8-T01 | reports/ux/interaction-time.json |
| REQ-SEC-001 | All cross-workspace access attempts are denied and logged without data leakage. | SAFE-003 | P3-T04, P8-T05 | reports/stage-a/security-hard-gates.json |
| REQ-SEC-002 | CSRF, session fixation, OAuth state and redirect attacks have regression tests. | Security runbook | P8-T05 | apps/api/tests/security/ |
| REQ-SEC-003 | File upload enforces size, MIME sniffing, quotas, malware adapter and resource limits. | Design §20 | P4-T01, P4-T02, P8-T05 | apps/api/tests/security/test_upload_pipeline.py |
| REQ-SEC-004 | Logs/traces never include tokens, raw source bodies, private notes or full prompts. | Design §25.4 | P8-T05, P8-T06 | tests/security/test_log_redaction.py |
| REQ-SEC-005 | Account/source deletion propagates to derived artifacts and is verifiable. | Design §25.5 | P8-T08 | reports/privacy/deletion-verification.json |
| REQ-SEC-006 | Backups are restorable and deletion tombstones are re-applied after restore. | Operational runbook | P8-T08 | reports/operations/restore-drill.json |
| REQ-OPS-001 | Non-LLM API P95 is 500 ms or less under the reference load. | Evaluation OPS-001 | P8-T06, P8-T10 | reports/stage-c/performance.json |
| REQ-OPS-002 | Chat first stream response P95 is 2 seconds or less. | Evaluation OPS-002 | P6-T08, P8-T10 | reports/stage-c/stream-latency.json |
| REQ-OPS-003 | Structured observability uses pseudonymous IDs and links API, worker, LLM and provider traces. | Design observability | P8-T01, P8-T06 | tests/observability/test_trace_linkage.py |
| REQ-OPS-004 | Production deploys separate Web, API and Worker processes with health/readiness checks. | Design §18.8 | P8-T07 | tests/deployment/test_runtime_contract.py |
| REQ-OPS-005 | Release decision is generated from immutable metric evidence and cannot lower thresholds after observation. | Evaluation release rules | P8-T02, P8-T03, P8-T04, P8-T10 | reports/release/final-gate-decision.json |
| REQ-OPS-006 | Pilot tooling captures baseline week and four agent weeks with consent and incident stop rules. | Evaluation pilot plan | P8-T09 | pilot/protocol/; reports/pilot/ |
| REQ-OPS-007 | Any Hard Gate violation blocks release regardless of aggregate score. | Evaluation Hard Gates | P8-T10 | reports/release/final-gate-decision.json |
| REQ-OPS-008 | Package and repository documents remain machine-verifiable and traceable to Tasks. | Development package | P0-T07, P8-T10 | scripts/verify_package.py; docs/requirements/requirements-traceability.md |

| REQ-FND-001 | Root toolchain and package managers are pinned and reproducible from a clean checkout. | Engineering standards | P0-T01 | tests/handoff/test_root_contract.py; lockfiles |
| REQ-FND-002 | Local PostgreSQL, Redis and S3-compatible infrastructure has health checks and persistent development data. | Architecture §18.8 | P0-T02 | tests/handoff/test_compose_contract.py; docker compose config |
| REQ-FND-003 | API exposes typed liveness/readiness endpoints without product-domain coupling. | Repository contract | P0-T04 | apps/api/tests/test_health.py |
| REQ-FND-004 | Worker boots with explicit settings, job registry and graceful shutdown contract. | Repository contract | P0-T05 | apps/worker/tests/test_boot.py |
| REQ-FND-005 | Web application boots with strict TypeScript, test baseline and generated-client boundary. | Repository contract | P0-T06 | apps/web/src/app/page.test.tsx; pnpm build |
| REQ-API-001 | Database settings, async sessions and Alembic migrations work against a fresh PostgreSQL instance. | Design §18–§19 | P3-T01 | apps/api/tests/integration/test_migration_bootstrap.py |
| REQ-API-002 | Repository adapters and Unit of Work preserve transaction boundaries and do not leak ORM types into domain contracts. | Architecture contract | P3-T03 | apps/api/tests/integration/test_unit_of_work.py |
| REQ-API-003 | OpenAPI is deterministic and the generated TypeScript client exactly matches the server contract. | Design §18.6 | P3-T09 | packages/api-client/tests/generated_contract.test.ts; openapi diff |
| REQ-AGT-001 | Every agent request has a typed operation and immutable step events from receipt through verification. | Design §15.1, §15.9 | P6-T01 | apps/api/tests/integration/test_agent_operation_events.py |
| REQ-AGT-002 | Context Builder retrieves the least necessary verified facts and separates untrusted source excerpts. | Design §22.4 | P6-T03 | apps/api/tests/unit/test_context_builder.py |

## Coverage summary

- Requirements: **104**
- Implementation Tasks referenced: **all nine Phases**
- Safety and quality metrics remain governed by the evaluation specification.
- Evidence paths are contracts for implementation; a release report must link the actual immutable artifacts.
