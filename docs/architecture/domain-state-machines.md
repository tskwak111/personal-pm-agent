# Domain State Machines and Authorization Matrix

This document turns the product terms into explicit transition contracts. Implementations may add metadata but may not bypass these transitions.

## 1. Task state machine

| From | To | Required predicate | Initiator | Approval |
|---|---|---|---|---|
| Draft | Planned | source/candidate accepted and required identifiers valid | user or low-risk policy | policy-dependent |
| Planned | Ready | `Blocks Start` predecessors complete; start time reached; required resources available | system | none |
| Ready | In Progress | user starts a Work Session | user | none |
| Ready | Deferred | flexible personal work intentionally moved | user or authorized agent | automatic only within policy |
| In Progress | Done | completion conditions acknowledged and evidence policy satisfied | user; system may propose | user confirmation for important outputs |
| In Progress | Waiting | progress requires an external person, approval or provider result | user or system proposal | none for status; external contact requires approval |
| In Progress | Blocked | an internal technical/information obstacle prevents progress | user or system proposal | none |
| In Progress | Ready | session stopped with remaining executable scope | user | none |
| Waiting | Ready | external dependency resolved and all other start predicates pass | system | none |
| Blocked | Ready | blocker resolved and all start predicates pass | user or verified system event | none |
| Planned/Ready/Waiting/Blocked | Cancelled | task no longer belongs to approved scope | user | confirmation when milestone impact exists |
| Deferred | Planned | defer-until condition reached | system | none |
| Done | In Progress | completion was reversed with reason and audit record | user | confirmation |
| Cancelled | Planned | task restored into approved scope | user | confirmation |

Forbidden examples:

- `Waiting → Done` without a completion command.
- `Done → Ready` without a reversal reason and audit event.
- `Draft → In Progress` before canonicalization.
- Any transition that crosses workspaces.

## 2. Milestone lifecycle

```text
Draft → Active → At Risk → Completed
              ↘ Blocked ↗
Draft/Active/At Risk/Blocked → Cancelled
```

- Risk labels are computed projections, not user-editable facts.
- A Hard Deadline cannot be shifted by a risk computation.
- Completion requires all mandatory completion conditions, or an explicit user override with reason.
- Scope re-baselining creates an immutable scope-change record; it does not rewrite historical progress.

## 3. Inbox lifecycle

```text
New → Queued → Processing → Structured
                    ├→ Needs Confirmation
                    ├→ Failed
                    └→ Ignored
Needs Confirmation → Structured | Ignored
Failed → Queued (new extraction version only)
```

Every retry creates a new processing attempt. Raw source bytes and prior extraction results remain immutable until a user-authorized retention deletion.

## 4. Proposal and Approval lifecycle

```text
Pending → Approved → Executing → Executed
        ├→ Rejected
        ├→ Expired
        └→ Superseded
Approved/Executing → Failed
```

An Approval binds:

- proposal ID and proposal version;
- actor/user ID and workspace ID;
- exact command payload hash;
- target object IDs and expected versions;
- granted action class;
- approval timestamp and expiry.

If any target version or command payload changes, the approval is invalid and the proposal must be regenerated.

## 5. Plan Snapshot lifecycle

```text
Candidate → Validated → Current
Candidate/Validated → Rejected
Current → Superseded
```

- Only a fully validated plan may become Current.
- A failed replan leaves the previous Current snapshot untouched.
- Plan snapshots are immutable and reference the exact Planner input digest, rule version and output digest.
- Undo creates a new snapshot based on a previous plan; it never mutates history.

## 6. External Execution lifecycle

```text
Pending → Executing → Succeeded
                    ├→ Retryable Failure → Pending
                    ├→ Needs Reauthorization
                    ├→ Permanent Failure
                    └→ Dead Letter
Pending → Cancelled
Succeeded → Compensating → Compensated | Compensation Failed
```

Success requires provider acknowledgement plus verification of the returned external object or durable provider operation ID. An HTTP 2xx without the expected external identity is not sufficient.

## 7. Calendar sync lifecycle

| State | Meaning |
|---|---|
| In Sync | Internal projection matches the latest known provider version. |
| Pending Outbound | Internal command committed; provider result not yet verified. |
| Pending Inbound | Provider change detected; internal reconciliation not finished. |
| Conflict | Field ownership or version rules cannot resolve safely. |
| Needs Reauthorization | Token/consent no longer permits the operation. |
| Failed | Non-recoverable sync failure; internal and external states shown separately. |
| Tombstoned | Provider object deleted; deletion identity retained for reconciliation. |

## 8. Authority matrix

| Action class | Default authority |
|---|---|
| classify input; calculate priority/risk; produce draft plan | automatic |
| create low-harm personal Task with calibrated evidence | automatic then notify |
| reschedule flexible low-priority personal Task outside frozen horizon | automatic then notify, user-configurable |
| change workstream/milestone scope; reduce required output | prior approval |
| create or move Google focus block | prior approval |
| change Hard Deadline; modify/delete Fixed Event | explicit re-confirmation |
| send message or submit external artifact | explicit re-confirmation |
| cancel project; irreversible/destructive action | explicit re-confirmation |

Prompt text or model confidence can never upgrade authority.

## 9. Cross-cutting invariants

1. Every command verifies actor, workspace ownership and expected object version.
2. Every accepted state change emits an Audit Event with before/after, reason, rule/approval basis and trace ID.
3. Facts, inferences, proposals, internal execution and external execution are distinct types and UI states.
4. Unknown time remains unknown; a date-only deadline is never silently converted to 23:59.
5. No Planner pass assigns one availability slot to more than one Task.
6. A dependency cycle is unresolved input, never a schedulable graph.
7. External content cannot invoke an application command.
