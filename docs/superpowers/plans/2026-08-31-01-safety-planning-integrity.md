# Safety and Planning Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate known scheduling, replanning, persistence-input, and false external-success violations.

**Architecture:** Fix invariants in shared deterministic functions, then hydrate those functions from workspace-scoped persistence. Protected prior allocations remain authoritative until an authorized proposal is accepted; unavailable executors fail closed.

**Tech Stack:** Python 3.13, frozen dataclasses, SQLAlchemy 2.x async, Alembic, pytest, Hypothesis

**Spec:** `docs/superpowers/specs/2026-08-31-aaa-production-readiness-design.md`

## Global Constraints

- Planner stays independent of FastAPI, SQLAlchemy, Redis, wall-clock time, system randomness, and global locale.
- Every mutation validates workspace ownership and object version.
- Failed planning never replaces the last valid plan.
- No unexecuted or unverified external action is reported as successful.
- Use existing dataclasses and services; add no provider abstraction or repository interface without two consumers.

---

### Task 1: Enforce BLOCKS_START completion time

**Files:**
- Modify: `packages/planner/src/personal_pm_planner/scheduling/serial.py:107-268`
- Test: `packages/planner/tests/scheduling/test_serial_schedule.py`
- Test: `packages/planner/tests/properties/test_planner_invariants.py`

**Interfaces:**
- Consumes: `start_gates: dict[TaskId, frozenset[TaskId]]`
- Produces: `serial_schedule(...)` where every successor starts at or after the maximum predecessor completion

- [ ] **Step 1: Write the failing regression**

```python
def test_blocks_start_successor_begins_after_predecessor_finishes() -> None:
    predecessor = make_schedulable(1, base_duration_minutes=60, start_after=DAY_START + timedelta(hours=4))
    successor = make_schedulable(2, base_duration_minutes=60)
    result = serial_schedule(
        tasks=(successor, predecessor),
        slots=build_unique_slots(
            AvailabilityContext(availability_windows=(make_window(8),), capacity_factor=1.0)
        ),
        duration_field="base_duration_minutes",
        start_gates={successor.id: frozenset({predecessor.id})},
    )
    pred_end = max(a.end_at for a in result.allocations if a.task_id == predecessor.id)
    succ_start = min(a.start_at for a in result.allocations if a.task_id == successor.id)
    assert succ_start >= pred_end
```

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest packages/planner/tests/scheduling/test_serial_schedule.py::test_blocks_start_successor_begins_after_predecessor_finishes -q`

Expected: FAIL because the successor occupies an earlier free slot.

- [ ] **Step 3: Implement the shared timing gate**

```python
completion_by_task: dict[TaskId, datetime] = {}

predecessor_end = max(
    (completion_by_task[p] for p in gates.get(task.id, ()) if p in completion_by_task),
    default=None,
)
produced = _place_task(
    ledger,
    task,
    required,
    pass_type,
    earliest_start=max(filter(None, (task.start_after, predecessor_end)), default=None),
)
if placed >= required and produced:
    completion_by_task[task.id] = max(item.end_at for item in produced)
```

Change `_place_task` to accept `earliest_start: datetime | None`; do not mutate `SchedulableTask`.

- [ ] **Step 4: Add a generated invariant**

For every `BLOCKS_START` edge whose endpoints are allocated, assert:

```python
assert min(successor_starts) >= max(predecessor_ends)
```

- [ ] **Step 5: Verify GREEN and adjacent passes**

Run:

```bash
uv run pytest packages/planner/tests/scheduling/test_serial_schedule.py packages/planner/tests/scheduling/test_passes.py packages/planner/tests/properties/test_planner_invariants.py -q
uv run mypy packages/planner/src
```

- [ ] **Step 6: Commit**

```bash
git add packages/planner/src/personal_pm_planner/scheduling/serial.py packages/planner/tests/scheduling/test_serial_schedule.py packages/planner/tests/properties/test_planner_invariants.py
git commit -m "fix(planner): enforce dependency completion timing"
```

### Task 2: Preserve pinned and freeze-window allocations

**Files:**
- Modify: `packages/planner/src/personal_pm_planner/scheduling/passes.py`
- Modify: `packages/planner/src/personal_pm_planner/replanning/optimize.py`
- Modify: `packages/planner/src/personal_pm_planner/planner.py`
- Modify: `packages/planner/src/personal_pm_planner/contracts/output.py`
- Test: `packages/planner/tests/replanning/test_replanning.py`
- Test: `packages/planner/tests/vectors/test_reference_vectors.py`

**Interfaces:**
- Produces: `ReplanOutcome.selected_passes: PlanningPasses`
- Produces: authoritative Planner output built from `selected_passes`, not a discarded fresh plan

- [ ] **Step 1: Extend the existing test to assert output allocations**

```python
output = plan(value)
allocation = next(a for a in output.base_plan.allocations if a.task_id == frozen_task)
assert allocation.start_at == snapshot.allocations[0].start_at
assert allocation.end_at == snapshot.allocations[0].end_at
assert "PROPOSAL_REQUIRED:USER_PINNED_MOVE_FORBIDDEN" in output.validation_warnings
```

Add the equivalent assertion for an unpinned allocation inside the freeze window.

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest packages/planner/tests/replanning/test_replanning.py -q`

Expected: FAIL because `planner.plan` returns fresh pass allocations.

- [ ] **Step 3: Build protected passes without double allocation**

Add helpers that:

1. select prior allocations whose task is pinned or whose start is inside the freeze window;
2. exclude those task IDs from rescheduling;
3. reserve their intervals in both ledgers;
4. merge typed `TaskAllocation` values into Base and Safety results;
5. recompute total allocated minutes and sort by `(start_at, task_id)`.

```python
@dataclass(frozen=True, slots=True)
class ReplanOutcome:
    before: ReplanMetrics
    after: ReplanMetrics
    diff: ReplanDiff
    applied_moves: tuple[AppliedMove, ...]
    proposals: tuple[object, ...]
    selected_passes: PlanningPasses
```

Choose protected passes whenever a disallowed move generated a proposal; otherwise choose the lower lexicographic valid candidate.

- [ ] **Step 4: Make `plan()` consume one authoritative pass set**

```python
outcome = run_replan(value)
passes = outcome.selected_passes
risks = calculate_risks(passes, risk_context)
today_view = build_today_plan(value, passes, risks)
```

Remove the earlier independent `run_planning_passes(value)` call.

- [ ] **Step 5: Verify**

```bash
uv run pytest packages/planner/tests/replanning packages/planner/tests/vectors packages/planner/tests/properties -q
uv run mypy packages/planner/src
```

- [ ] **Step 6: Commit**

```bash
git add packages/planner/src/personal_pm_planner packages/planner/tests/replanning packages/planner/tests/vectors
git commit -m "fix(planner): preserve protected prior allocations"
```

### Task 3: Persist and hydrate every Planner input

**Files:**
- Modify: `apps/api/src/personal_pm_api/workspaces/models.py`
- Modify: `apps/api/src/personal_pm_api/planning/models.py`
- Create: `apps/api/migrations/versions/0010_planner_input_facts.py`
- Modify: `apps/api/src/personal_pm_api/planning/service.py`
- Test: `apps/api/tests/integration/test_schema_constraints.py`
- Test: `apps/api/tests/integration/test_planning_service.py`

**Interfaces:**
- Produces: workspace `timezone: str`
- Produces: workspace-scoped task dependencies, external dependencies/affected tasks, excluded dates
- Consumes: latest valid `PlanSnapshotModel.output_json["base_allocations"]` as `PriorPlanSnapshot`

- [ ] **Step 1: Write the hydration regression**

Seed one calendar event, one `BLOCKS_START` edge, one external dependency, one excluded date, a pinned task, a non-default timezone, and a prior plan. Capture `PlanningService._run_planner` input and assert:

```python
assert captured.user_timezone == "America/New_York"
assert len(captured.calendar_events) == 1
assert len(captured.task_dependencies) == 1
assert len(captured.external_dependencies) == 1
assert captured.pinned_task_ids == frozenset({TaskId(pinned_id)})
assert captured.excluded_dates == (date(2026, 9, 7),)
assert captured.prior_plan_snapshot is not None
```

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/integration/test_planning_service.py -q`

Expected: FAIL on the first missing persisted input.

- [ ] **Step 3: Add the minimum normalized persistence**

Migration `0010` must:

- add `workspaces.timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Seoul'`;
- add `workspace_id` to `task_dependencies` and enforce workspace FK/index;
- add `external_dependencies`, `external_dependency_tasks`, and `workspace_excluded_dates`;
- add `(deadline_time_known = true) OR (deadline_at IS NULL)` to tasks;
- reject dependency endpoints outside the declared workspace in service/repository validation.

Use a role column `affected|fallback` in `external_dependency_tasks`; do not store UUID arrays in JSON.

- [ ] **Step 4: Map rows to existing Planner dataclasses**

Implement private mapping functions in `planning/service.py` for `CalendarEventSnapshot`, `TaskDependency`, `ExternalDependencySnapshot`, and `PriorPlanSnapshot`. Parse ISO datetimes with `datetime.fromisoformat` and UUID hex with `UUID(hex=value)`; reject malformed prior snapshots and preserve the last valid plan.

- [ ] **Step 5: Verify migration and planning integration**

```bash
APP_ENVIRONMENT=test PM_DATABASE_URL="postgresql+asyncpg://personal_pm:local_only_password@localhost:15432/personal_pm" uv run pytest apps/api/tests/integration/test_schema_constraints.py apps/api/tests/integration/test_planning_service.py -q
APP_ENVIRONMENT=test PM_DATABASE_URL="postgresql+asyncpg://personal_pm:local_only_password@localhost:15432/personal_pm" uv run alembic -c apps/api/alembic.ini check
uv run mypy apps/api/src
```

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/personal_pm_api/workspaces/models.py apps/api/src/personal_pm_api/planning/models.py apps/api/src/personal_pm_api/planning/service.py apps/api/migrations/versions/0010_planner_input_facts.py apps/api/tests/integration/test_schema_constraints.py apps/api/tests/integration/test_planning_service.py
git commit -m "feat(planning): hydrate persisted planner facts"
```

### Task 4: Fail closed without an external executor

**Files:**
- Modify: `apps/api/src/personal_pm_api/agent/orchestrator.py:103-149`
- Test: `apps/api/tests/integration/test_orchestrator_flow.py`

**Interfaces:**
- Produces: `OperationResult(status="FAILED", external_action_executed=False, user_message_code="EXTERNAL_EXECUTOR_UNAVAILABLE")`

- [ ] **Step 1: Write the failing test**

```python
async def test_missing_external_executor_never_reports_success(orch_env) -> None:
    result = await orch_env["orchestrator"].handle(
        orch_env["actor"],
        text="실행해줘",
        approved_proposal_id=orch_env["proposal"],
    )
    assert result.status == "FAILED"
    assert result.external_action_executed is False
    assert result.user_message_code == "EXTERNAL_EXECUTOR_UNAVAILABLE"
    assert result.events[-1] == StepEvent(step="VERIFY", status="FAILED")
```

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/integration/test_orchestrator_flow.py::test_missing_external_executor_never_reports_success -q`

Expected: FAIL with `status == "SUCCEEDED"`.

- [ ] **Step 3: Replace simulated success with one guard**

```python
if self._external_executor is None:
    events.append(StepEvent(step="VERIFY", status="FAILED"))
    return OperationResult(
        status="FAILED",
        events=tuple(events),
        external_action_executed=False,
        authorization_level=review.level,
        user_message_code="EXTERNAL_EXECUTOR_UNAVAILABLE",
    )
```

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest apps/api/tests/integration/test_orchestrator_flow.py apps/worker/tests/calendar -q
git add apps/api/src/personal_pm_api/agent/orchestrator.py apps/api/tests/integration/test_orchestrator_flow.py
git commit -m "fix(agent): fail closed without external executor"
```

### Task 5: Enforce local-day and calendar workspace boundaries

**Files:**
- Modify: `packages/planner/src/personal_pm_planner/today.py:45-56`
- Modify: `apps/api/src/personal_pm_api/calendar/sync.py:120-136`
- Test: `packages/planner/tests/replanning/test_replanning.py`
- Test: `apps/api/tests/integration/test_calendar_conflicts.py`

**Interfaces:**
- Produces: today membership by `allocation.start_at.astimezone(ZoneInfo(user_timezone)).date()`
- Produces: `apply_provider_deletion(workspace_id, external_event_id)`

- [ ] **Step 1: Write timezone-boundary and cross-workspace tests**

```python
assert allocation.start_at.date() != local_now_date
assert allocation.start_at.astimezone(ZoneInfo(value.user_timezone)).date() == local_now_date
assert task_id in build_today_plan(value, passes, risks).must_do
```

Create equal provider event IDs in two workspaces, delete one through its workspace ID, and assert the other remains `SYNCED`.

- [ ] **Step 2: Confirm RED**

```bash
uv run pytest packages/planner/tests/replanning/test_replanning.py apps/api/tests/integration/test_calendar_conflicts.py -q
```

- [ ] **Step 3: Fix the shared comparisons and query**

Convert allocation instants to `value.user_timezone` before comparing dates. Add `workspace_id` to the deletion method and SQL predicate; update every caller.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest packages/planner/tests/replanning/test_replanning.py apps/api/tests/integration/test_calendar_conflicts.py apps/api/tests/integration/test_calendar_import.py -q
git add packages/planner/src/personal_pm_planner/today.py packages/planner/tests/replanning/test_replanning.py apps/api/src/personal_pm_api/calendar/sync.py apps/api/tests/integration/test_calendar_conflicts.py
git commit -m "fix(time): enforce local day and workspace scope"
```

### Task 6: Record stream evidence

**Files:**
- Modify: `docs/status/VERIFICATION_EVIDENCE.md`
- Modify: `docs/requirements/requirements-traceability.md`
- Modify: `docs/status/RISK_REGISTER.md`

- [ ] **Step 1: Run the stream gate**

```bash
make format-check
make lint
make typecheck
make test-unit
make test-integration
git diff --check
```

- [ ] **Step 2: Record exact revision, command, exit code, and test counts**

Mark PLAN-002, PLAN-006/007/009, SAFE-004, and pin/freeze evidence with real test paths. Reopen any risk whose external proof is still absent.

- [ ] **Step 3: Commit**

```bash
git add docs/status/VERIFICATION_EVIDENCE.md docs/requirements/requirements-traceability.md docs/status/RISK_REGISTER.md
git commit -m "docs(safety): record planning integrity evidence"
```
