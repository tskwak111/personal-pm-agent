# Definition of Done

A Task is complete only when every applicable item below has fresh evidence. “Code written” is not completion.

## 1. Requirement and design

- The Task has a stable ID and maps to one or more requirements or metrics.
- The implementation follows the approved spec and Phase interface contract.
- New architectural choices are recorded in the Decision Log or an ADR.
- No scope, authority or quality threshold was silently weakened.

## 2. TDD evidence

- A focused test was written before implementation.
- The intended failure was observed and recorded in the work log/commit history.
- Minimum implementation made the focused test pass.
- Adjacent regression tests pass.
- Bug fixes include a regression test that fails when the fix is reverted.

## 3. Code and data safety

- Types are explicit; Python mypy strict and TypeScript strict pass.
- Workspace ownership and optimistic concurrency are enforced on state changes.
- Logs contain no token, source document body, private note or full prompt.
- Migrations are forward-tested and have a documented recovery path.
- External actions are idempotent, audited and verified.
- LLM output remains candidate data until deterministic validation and authority checks finish.

## 4. Product truthfulness

- UI distinguishes internal save, pending external sync, external success and failure.
- Unknown or uncertain values are not presented as verified facts.
- Automatic changes expose reason, authority basis and undo capability where applicable.
- Error and empty states provide a safe next action.

## 5. Verification

Run every applicable command from `docs/quality/verification-command-matrix.md`. Capture command, timestamp, commit SHA, exit code and summary in the Task completion record.

## 6. Documentation and handoff

- Phase checklist and `IMPLEMENTATION_STATUS.md` are updated.
- Requirement traceability points to the implemented test/evidence.
- API/OpenAPI/client/schema documents are regenerated when contracts change.
- Risk Register is updated for newly discovered product or operational risk.
- Commits are atomic and use the repository convention.

## 7. Prohibited completion claims

Do not claim completion based on:

- a prior test run;
- a subset of the required suite;
- an agent or subagent report without independent inspection;
- a successful lint run when build/tests were required;
- screenshots without machine-verifiable state;
- assumed external API success.
