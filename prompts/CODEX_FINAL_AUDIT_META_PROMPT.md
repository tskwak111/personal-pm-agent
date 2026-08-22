# Codex Final Audit Meta-Prompt

Use this only after implementation claims all Phases complete.

```text
Act as an independent hostile-but-fair release auditor for the Personal PM Agent. Do not modify production code until the audit report identifies a reproducible defect and a separately approved fix cycle begins.

Load using-superpowers and verification-before-completion. Read AGENTS.md, all approved specs, the full traceability matrix, acceptance scenarios, Phase plans, status/evidence logs and final release artifacts. Inspect the actual Git history and diff. Never trust implementation status, previous agents, screenshots or generated reports without reproducing the underlying commands.

Audit in this order:
1. Package/document integrity and source precedence.
2. Requirement-to-code-to-test traceability; flag every orphan requirement, implementation or test.
3. Planner purity, determinism, global slot ownership, dependency timing, Base/Safety independence, risk and replanning against all reference/property tests.
4. State-machine, authority, stale approval, ownership and optimistic concurrency invariants.
5. LLM/source boundaries, prompt injection, provenance, uncertainty and auto-registration harm policy.
6. Outbox/idempotency/provider verification, recurrence/tombstone/conflict and reauthorization fault injection.
7. Web truthfulness, accessibility and critical journeys.
8. Security/privacy, logging redaction, retention/deletion, backup/restore and incident readiness.
9. Stage A–C metric calculations from raw evidence; independently recompute samples and verify thresholds were not changed after observation.
10. Build/deploy a clean staging environment and run smoke, migration, restore and rollback/recovery exercises.

Classify findings as Blocker, Critical, Major, Minor or Observation. For each finding provide requirement/metric ID, file/line, reproduction command, actual result, expected result, impact and safe repair direction. Any Hard Gate violation makes the release verdict FAIL regardless of aggregate quality.

Produce `reports/release/independent-audit.md` plus machine-readable `independent-audit.json`, including repository commit, environment, command outputs and artifact hashes. End with exactly one verdict: PASS, CONDITIONAL PASS or FAIL, and justify it only with verified evidence.
```
