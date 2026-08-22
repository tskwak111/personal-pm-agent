# Phase 1 — Planning Core Domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement framework-independent canonical domain snapshots, task state transitions, dependency semantics, authority policy and auditable proposal contracts consumed by the Planner and API.

**Architecture:** The Planner package owns immutable snapshots and pure policies. Persistence and HTTP representations convert to and from these contracts later; no ORM, FastAPI or provider type enters this Phase.

**Tech Stack:** Python 3.13 standard library, frozen dataclasses, Enum, UUID, zoneinfo, pytest and Hypothesis.

**Spec:** Design sections 5, 7, 8 and 14; Planner Spec sections 2, 3, 4, 6 and 17.

## Global Constraints

- Follow `AGENTS.md` and `docs/architecture/decision-precedence.md`.
- Never weaken Planner or Evaluation gates.
- Use TDD: failing test, confirmed failure, minimum implementation, focused pass, adjacent regression, commit.
- Keep files focused and interfaces explicit.
- Update `docs/status/IMPLEMENTATION_STATUS.md` after every completed Task.
- Do not claim completion without fresh command output.

---

## Locked File Map

```text
packages/planner/src/personal_pm_planner/domain/
├─ enums.py
├─ identifiers.py
├─ time.py
├─ facts.py
├─ work.py
├─ task.py
├─ state_machine.py
├─ dependency.py
├─ availability.py
├─ approval.py
├─ audit.py
├─ authorization.py
└─ errors.py
packages/planner/src/personal_pm_planner/contracts/
├─ input.py
└─ output.py
```

### Task P1-T01: Define canonical identifiers, enums and aware-time primitives

**Files:**
- Create: `packages/planner/src/personal_pm_planner/domain/identifiers.py`
- Create: `packages/planner/src/personal_pm_planner/domain/enums.py`
- Create: `packages/planner/src/personal_pm_planner/domain/time.py`
- Create: `packages/planner/tests/domain/test_primitives.py`

**Interfaces:**
- Consumes: Python standard library only
- Produces: `WorkspaceId`, canonical enums and UTC-aware validation helpers

- [x] **Step 1: Write the failing test**

```python
from datetime import datetime
from uuid import UUID
import pytest
from personal_pm_planner.domain.identifiers import WorkspaceId
from personal_pm_planner.domain.time import require_aware_utc

def test_identifiers_are_typed_uuid_values() -> None:
    raw = UUID("00000000-0000-0000-0000-000000000001")
    assert WorkspaceId(raw).value == raw

def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        require_aware_utc(datetime(2026, 8, 23, 12, 0))
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/domain/test_primitives.py -q
```

Expected: FAIL because canonical primitives do not exist.

- [x] **Step 3: Implement the minimum contract**

```python
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

@dataclass(frozen=True, slots=True, order=True)
class WorkspaceId:
    value: UUID


def require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc)
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/domain/test_primitives.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run ruff check packages/planner && uv run mypy packages/planner/src
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/domain/identifiers.py packages/planner/src/personal_pm_planner/domain/enums.py packages/planner/src/personal_pm_planner/domain/time.py packages/planner/tests/domain/test_primitives.py
git commit -m "feat(domain): add canonical identifiers and time primitives"
```

### Task P1-T02: Model facts, workstreams and milestones as immutable snapshots

**Files:**
- Create: `packages/planner/src/personal_pm_planner/domain/facts.py`
- Create: `packages/planner/src/personal_pm_planner/domain/work.py`
- Create: `packages/planner/tests/domain/test_work_snapshots.py`

**Interfaces:**
- Consumes: canonical IDs, enums and aware time
- Produces: `SourceFact`, `AreaSnapshot`, `WorkstreamSnapshot`, `MilestoneSnapshot`

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner.domain.work import MilestoneSnapshot

def test_date_only_deadline_does_not_fabricate_time(milestone_factory) -> None:
    milestone: MilestoneSnapshot = milestone_factory(deadline_date="2026-09-10", deadline_at=None)
    assert milestone.deadline_date_known is True
    assert milestone.deadline_time_known is False
    assert milestone.deadline_at is None
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/domain/test_work_snapshots.py -q
```

Expected: FAIL because milestone snapshots are missing.

- [x] **Step 3: Implement the minimum contract**

```python
@dataclass(frozen=True, slots=True)
class MilestoneSnapshot:
    id: MilestoneId
    workspace_id: WorkspaceId
    workstream_id: WorkstreamId
    title: str
    deadline_date: date | None
    deadline_at: datetime | None
    deadline_date_known: bool
    deadline_time_known: bool
    deadline_type: DeadlineType
    required_buffer_minutes: int
    version: int

    def __post_init__(self) -> None:
        if self.deadline_time_known and self.deadline_at is None:
            raise ValueError("known deadline time requires deadline_at")
        if not self.deadline_time_known and self.deadline_at is not None:
            raise ValueError("unknown deadline time cannot persist a factual deadline_at")
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/domain/test_work_snapshots.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/domain -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/domain/facts.py packages/planner/src/personal_pm_planner/domain/work.py packages/planner/tests/domain/test_work_snapshots.py
git commit -m "feat(domain): add workstream and milestone snapshots"
```

### Task P1-T03: Implement Task snapshot and explicit state machine

**Files:**
- Create: `packages/planner/src/personal_pm_planner/domain/task.py`
- Create: `packages/planner/src/personal_pm_planner/domain/state_machine.py`
- Create: `packages/planner/tests/domain/test_task_state_machine.py`

**Interfaces:**
- Consumes: workstream and milestone snapshots
- Produces: `TaskSnapshot`, `TaskTransitionRequest`, `transition_task` with guarded state transitions

- [x] **Step 1: Write the failing test**

```python
import pytest
from personal_pm_planner.domain.enums import TaskStatus
from personal_pm_planner.domain.state_machine import transition_task

def test_waiting_task_cannot_become_ready_while_external_wait_remains(task_factory) -> None:
    task = task_factory(status=TaskStatus.WAITING, waiting_reason="external:dataset")
    with pytest.raises(ValueError, match="waiting condition"):
        transition_task(task, TaskStatus.READY, waiting_resolved=False)

def test_done_requires_zero_remaining_minutes(task_factory) -> None:
    task = task_factory(status=TaskStatus.IN_PROGRESS, remaining_base_minutes=30)
    with pytest.raises(ValueError, match="remaining"):
        transition_task(task, TaskStatus.DONE, completion_confirmed=True)
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/domain/test_task_state_machine.py -q
```

Expected: FAIL because the state machine is absent.

- [x] **Step 3: Implement the minimum contract**

```python
ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.DRAFT: frozenset({TaskStatus.PLANNED, TaskStatus.CANCELLED}),
    TaskStatus.PLANNED: frozenset({TaskStatus.READY, TaskStatus.DEFERRED, TaskStatus.CANCELLED}),
    TaskStatus.READY: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.WAITING, TaskStatus.BLOCKED, TaskStatus.DEFERRED}),
    TaskStatus.IN_PROGRESS: frozenset({TaskStatus.DONE, TaskStatus.WAITING, TaskStatus.BLOCKED, TaskStatus.READY}),
    TaskStatus.WAITING: frozenset({TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.BLOCKED: frozenset({TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.DONE: frozenset({TaskStatus.IN_PROGRESS}),
    TaskStatus.DEFERRED: frozenset({TaskStatus.PLANNED, TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.CANCELLED: frozenset({TaskStatus.PLANNED}),
}
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/domain/test_task_state_machine.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/domain -q && uv run mypy packages/planner/src
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/domain/task.py packages/planner/src/personal_pm_planner/domain/state_machine.py packages/planner/tests/domain/test_task_state_machine.py
git commit -m "feat(domain): enforce task state transitions"
```

### Task P1-T04: Model task dependencies and cycle result contracts

**Files:**
- Create: `packages/planner/src/personal_pm_planner/domain/dependency.py`
- Create: `packages/planner/src/personal_pm_planner/domain/errors.py`
- Create: `packages/planner/tests/domain/test_dependencies.py`

**Interfaces:**
- Consumes: Task IDs and dependency enums
- Produces: `TaskDependency`, `DependencyGraph`, `DependencyCycle` and stable cycle reporting

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner.domain.dependency import DependencyGraph, TaskDependency
from personal_pm_planner.domain.enums import DependencyType

def test_cycle_path_is_stable(task_ids) -> None:
    a, b, c = task_ids(3)
    graph = DependencyGraph.from_dependencies([
        TaskDependency(a, b, DependencyType.BLOCKS_START),
        TaskDependency(b, c, DependencyType.BLOCKS_START),
        TaskDependency(c, a, DependencyType.BLOCKS_START),
    ])
    assert graph.cycles()[0].task_ids == tuple(sorted((a, b, c)))
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/domain/test_dependencies.py -q
```

Expected: FAIL because dependency graph contracts are missing.

- [x] **Step 3: Implement the minimum contract**

```python
@dataclass(frozen=True, slots=True)
class TaskDependency:
    predecessor_id: TaskId
    successor_id: TaskId
    dependency_type: DependencyType

@dataclass(frozen=True, slots=True)
class DependencyCycle:
    task_ids: tuple[TaskId, ...]

class DependencyGraph:
    def __init__(self, dependencies: tuple[TaskDependency, ...]) -> None:
        self.dependencies = tuple(sorted(dependencies, key=lambda item: (
            item.predecessor_id.value.hex,
            item.successor_id.value.hex,
            item.dependency_type.value,
        )))
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/domain/test_dependencies.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/domain -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/domain/dependency.py packages/planner/src/personal_pm_planner/domain/errors.py packages/planner/tests/domain/test_dependencies.py
git commit -m "feat(domain): add dependency graph contracts"
```

### Task P1-T05: Define availability, calendar and external dependency snapshots

**Files:**
- Create: `packages/planner/src/personal_pm_planner/domain/availability.py`
- Create: `packages/planner/tests/domain/test_availability_snapshots.py`

**Interfaces:**
- Consumes: aware time primitives and Task IDs
- Produces: `AvailabilityWindow`, `CalendarEventSnapshot`, `ExternalDependencySnapshot` with invariant validation

- [x] **Step 1: Write the failing test**

```python
import pytest
from personal_pm_planner.domain.availability import AvailabilityWindow

def test_availability_requires_positive_window(aware_datetime) -> None:
    start = aware_datetime(12, 0)
    with pytest.raises(ValueError, match="end must be after start"):
        AvailabilityWindow(start_at=start, end_at=start, tags=frozenset())
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/domain/test_availability_snapshots.py -q
```

Expected: FAIL because availability contracts are absent.

- [x] **Step 3: Implement the minimum contract**

```python
@dataclass(frozen=True, slots=True)
class AvailabilityWindow:
    start_at: datetime
    end_at: datetime
    tags: frozenset[str]

    def __post_init__(self) -> None:
        require_aware_utc(self.start_at)
        require_aware_utc(self.end_at)
        if self.end_at <= self.start_at:
            raise ValueError("end must be after start")
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/domain/test_availability_snapshots.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/domain -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/domain/availability.py packages/planner/tests/domain/test_availability_snapshots.py
git commit -m "feat(domain): add availability and external dependency snapshots"
```

### Task P1-T06: Implement proposal, approval, audit and authorization policy

**Files:**
- Create: `packages/planner/src/personal_pm_planner/domain/approval.py`
- Create: `packages/planner/src/personal_pm_planner/domain/audit.py`
- Create: `packages/planner/src/personal_pm_planner/domain/authorization.py`
- Create: `packages/planner/tests/domain/test_authorization.py`

**Interfaces:**
- Consumes: canonical action and deadline enums
- Produces: `authorization_level(action)`, version-bound Approval and immutable AuditEvent

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner.domain.authorization import authorization_level
from personal_pm_planner.domain.enums import ActionType, AuthorizationLevel

def test_hard_deadline_change_requires_reconfirmation() -> None:
    assert authorization_level(ActionType.CHANGE_HARD_DEADLINE) is AuthorizationLevel.RECONFIRM

def test_priority_calculation_is_automatic() -> None:
    assert authorization_level(ActionType.CALCULATE_PRIORITY) is AuthorizationLevel.AUTOMATIC
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/domain/test_authorization.py -q
```

Expected: FAIL because the policy table is missing.

- [x] **Step 3: Implement the minimum contract**

```python
AUTHORIZATION_POLICY: dict[ActionType, AuthorizationLevel] = {
    ActionType.CLASSIFY_INPUT: AuthorizationLevel.AUTOMATIC,
    ActionType.CALCULATE_PRIORITY: AuthorizationLevel.AUTOMATIC,
    ActionType.RESCHEDULE_LOW_RISK_TASK: AuthorizationLevel.AUTOMATIC_NOTIFY,
    ActionType.CREATE_FOCUS_BLOCK: AuthorizationLevel.APPROVAL,
    ActionType.CHANGE_HARD_DEADLINE: AuthorizationLevel.RECONFIRM,
    ActionType.CHANGE_FIXED_EVENT: AuthorizationLevel.RECONFIRM,
    ActionType.SEND_EXTERNAL_MESSAGE: AuthorizationLevel.RECONFIRM,
    ActionType.CANCEL_PROJECT: AuthorizationLevel.RECONFIRM,
}

def authorization_level(action: ActionType) -> AuthorizationLevel:
    return AUTHORIZATION_POLICY[action]
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/domain/test_authorization.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/domain -q && uv run mypy packages/planner/src
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/domain/approval.py packages/planner/src/personal_pm_planner/domain/audit.py packages/planner/src/personal_pm_planner/domain/authorization.py packages/planner/tests/domain/test_authorization.py
git commit -m "feat(domain): add approval and authority policies"
```

### Task P1-T07: Freeze Planner input and output contracts

**Files:**
- Create: `packages/planner/src/personal_pm_planner/contracts/input.py`
- Create: `packages/planner/src/personal_pm_planner/contracts/output.py`
- Modify: `packages/planner/src/personal_pm_planner/__init__.py`
- Create: `packages/planner/tests/contracts/test_contract_serialization.py`
- Create: `evals/planner-vectors/schema/planner-input.schema.json`
- Create: `evals/planner-vectors/schema/planner-output.schema.json`

**Interfaces:**
- Consumes: all Phase 1 immutable snapshots
- Produces: `PlannerInput`, `PlannerOutput`, canonical serialization and public package exports

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner import PlannerInput
from personal_pm_planner.contracts.input import canonical_input_bytes

def test_canonical_input_is_independent_of_collection_order(planner_input_factory) -> None:
    first = planner_input_factory(reverse_tasks=False)
    second = planner_input_factory(reverse_tasks=True)
    assert canonical_input_bytes(first) == canonical_input_bytes(second)
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/contracts/test_contract_serialization.py -q
```

Expected: FAIL because Planner contracts and canonical serialization are absent.

- [x] **Step 3: Implement the minimum contract**

```python
def canonical_input_bytes(value: PlannerInput) -> bytes:
    payload = to_canonical_primitive(value)
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def input_hash(value: PlannerInput) -> str:
    return hashlib.sha256(canonical_input_bytes(value)).hexdigest()
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/contracts/test_contract_serialization.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests -q && uv run ruff check packages/planner && uv run mypy packages/planner/src
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/contracts/input.py packages/planner/src/personal_pm_planner/contracts/output.py packages/planner/src/personal_pm_planner/__init__.py packages/planner/tests/contracts/test_contract_serialization.py evals/planner-vectors/schema/planner-input.schema.json evals/planner-vectors/schema/planner-output.schema.json
git commit -m "feat(domain): freeze Planner input and output contracts"
```

## Phase 1 Exit Criteria

- [x] Planner public snapshots are immutable and framework-independent.
- [x] Task transition tests cover every allowed and forbidden edge.
- [x] Dependency types and cycle results are stable.
- [x] Authorization policy matches the design spec.
- [x] Date-only deadlines cannot carry a fabricated factual time.
- [x] Canonical Planner input serialization is order-independent.
- [x] Phase 2 can consume only committed Phase 1 contracts.
