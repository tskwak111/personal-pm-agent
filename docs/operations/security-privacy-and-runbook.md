# Security, Privacy and Operational Runbook

## 1. Data classification

| Class | Examples | Minimum controls |
|---|---|---|
| Restricted | OAuth refresh tokens, encryption keys | dedicated encrypted secret/token store, no application logs, strict service access |
| Sensitive personal | calendar details, private tasks, uploaded files, meeting notes | encryption in transit/at rest, workspace isolation, retention/delete support |
| Derived sensitive | extracted text, embeddings, inferred risk and work patterns | same ownership as source; provenance and deletion linkage |
| Operational | trace IDs, latency, error class, model/prompt version | pseudonymous identifiers; no raw source content |
| Public | product documentation | integrity and version control |

## 2. Authentication and authorization

- Browser clients explicitly attach bearer sessions in the `Authorization` header; the API does not accept ambient authentication cookies.
- CSRF tokens are not applicable to the current bearer-only mode. Introduce SameSite/HTTP-only cookies and CSRF defenses together if cookie authentication is added.
- OAuth state, PKCE and redirect URI checks are mandatory.
- Provider scopes are incremental: calendar read before calendar write.
- Every repository query is scoped by workspace; object IDs alone never authorize access.
- Destructive or high-impact commands require expected version and the correct approval class.

## 3. Secret and token handling

- OAuth refresh/access tokens are encrypted with a separately managed key.
- Tokens and keys never appear in logs, traces, analytics, test fixtures or LLM context.
- Key rotation supports re-wrapping stored ciphertext and records an audit event.
- Connection removal revokes provider consent when possible and destroys local token material.

## 4. File and prompt-injection boundary

1. Enforce content length, MIME sniffing, extension policy and per-user quotas before parsing.
2. Store original bytes immutably and scan with an anti-malware adapter.
3. Run parsers in a constrained worker with resource/time limits.
4. Label extracted content `UNTRUSTED_SOURCE_CONTENT`.
5. Document text can create candidates only; it cannot select tools, authority or recipients.
6. All candidate commands pass schema, provenance, conflict, ownership, version and authority policies.

Runtime configuration uses `S3_ENDPOINT`, `S3_REGION`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` and `REDIS_URL`. Production rejects local object-storage credentials, non-HTTPS object storage and local Redis URLs. A successful upload means both the scanned bytes and metadata were persisted; storage failure cannot create a source record.

## 5. Retention and deletion

- Retention periods are configuration-backed and documented in product policy.
- Deleting a source cascades to extraction text, embeddings and derived candidates unless a legal/contractual retention reason is recorded.
- Account deletion creates a tracked deletion job across PostgreSQL, object storage, cache and analytics identifiers.
- Backups age out according to the published retention window; restore tooling prevents resurrecting deleted accounts without reapplying deletion tombstones.
- Every deletion run emits a verifiable report without retaining deleted content.

## 6. Backup and recovery targets

Initial release targets, validated in P8-T08:

- PostgreSQL RPO: 24 hours or better.
- PostgreSQL RTO: 4 hours or better.
- Object storage versioning/backup consistent with source retention policy.
- Quarterly restoration drill before general availability, and before each material schema migration.
- Recovery restores canonical state, audit linkage, outbox status and encryption-key access.

## 7. Incident severity

| Severity | Example | Initial action |
|---|---|---|
| SEV-0 | cross-workspace data exposure; unauthorized external submission | stop affected writes, preserve evidence, revoke credentials, notify incident owner immediately |
| SEV-1 | unauthorized calendar modification; prompt injection reaches a tool | disable affected automation, rotate relevant secrets, run impact analysis |
| SEV-2 | planner produces capacity/ordering invariant violation | freeze plan publication, keep last valid plan, reproduce and patch |
| SEV-3 | non-critical sync or notification degradation | queue/retry within policy and communicate truthful status |

Use `docs/templates/INCIDENT_TEMPLATE.md`. Do not delete audit evidence during incident response.

## 8. External-provider outage

- Keep internal Planning Core available when safe.
- Mark outbound state Pending/Failed/Needs Reauthorization accurately.
- Do not repeatedly notify or create duplicate provider objects.
- Reconcile with provider before announcing recovery.
- Preserve the user's last verified external state and disclose staleness.

## 9. Planner failure

- Reject the candidate output.
- Keep the last validated Current Plan Snapshot.
- Emit typed failure and trace ID.
- Disable automatic rescheduling if an invariant was violated.
- Run reference and property suites before re-enabling.

## 10. Release security gate

Release is blocked by any unresolved Hard Gate violation, critical/high known vulnerability without accepted mitigation, failed restore drill, missing data deletion verification, or inability to distinguish internal and external execution state.
