# Verification Command Matrix

Phase 0 implements these stable targets. Until then, use the underlying commands specified in the Phase plan.

| Change type | Focused evidence | Adjacent evidence | Completion evidence |
|---|---|---|---|
| Planner domain | focused `pytest` node | `pytest packages/planner/tests/unit -q` | `make verify-planner` |
| Planner algorithm | reference vector or property test | all Planner unit/property tests | Stage A report + deterministic replay |
| ORM/migration | repository/migration test | API integration tests against PostgreSQL | migrate fresh DB + rollback/recovery drill where supported |
| FastAPI endpoint | route contract test | API unit/integration + OpenAPI diff | `make verify-api` |
| LLM structuring | schema/golden example | golden split without test leakage | Stage B report |
| File processing | parser/storage test | malware/size/failure scenarios | file pipeline E2E |
| Calendar/external execution | adapter fake test | outbox/idempotency/fault injection | Stage C report |
| Worker/scheduler | job test with fake clock | retry/dead-letter suite | worker integration suite |
| React component | Vitest/Testing Library | feature tests + axe | `make verify-web` |
| Critical user journey | focused Playwright spec | full critical E2E | browser matrix + accessibility report |
| Security control | exploit/regression test | security suite/scanners | security release report |
| Deployment/operations | config test | staging smoke/fault drill | backup restore + release checklist |
| Documentation only | package/document verifier | link/Markdown parse | `make verify-docs` |

## Required root commands

```bash
make bootstrap
make format-check
make lint
make typecheck
make test-unit
make test-integration
make test-e2e
make build
make verify-planner
make verify-api
make verify-web
make verify-docs
make verify
```

## Evidence record format

```text
Timestamp (UTC):
Commit SHA:
Task ID:
Command:
Exit code:
Tests passed/failed/skipped:
Artifact/report path:
Reviewer notes:
```

A command is evidence only when it was run against the claimed commit or an uncommitted diff that is explicitly shown.

## Traceability evidence rules

- Local evidence uses an existing repository-relative path, optionally followed by `::pytest_node`.
- A requirement without local implementation says `Not Implemented` and must not cite a placeholder file.
- Evidence that can only be produced with credentials, private data, production infrastructure, or real users says `BLOCKED_EXTERNAL` and names the exact missing proof.
- `python3 scripts/verify_repo.py` rejects missing paths, unknown pytest nodes, repository escapes, and unsupported `Complete` claims.
