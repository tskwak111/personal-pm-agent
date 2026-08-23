# Phase 2 — Deterministic Planner Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Planner Spec v1.0 exactly: normalized input, unique availability slots, dependency timing, deterministic priority, global Base/Safety scheduling, risk, today plan, minimal-change replanning and overload proposals.

**Architecture:** A pure function `plan(PlannerInput) -> PlannerOutput` coordinates small deterministic modules. Every decision emits stable Rule IDs and evidence; failure returns typed unresolved items and preserves the prior valid plan.

**Tech Stack:** Python 3.13 standard library, dataclasses, graph algorithms, pytest, Hypothesis and deterministic benchmark fixtures.

**Spec:** Entire `docs/specs/2026-08-23-personal-pm-agent-planner-normative-spec.md`; Evaluation PLAN and PQ metrics.

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
packages/planner/src/personal_pm_planner/
├─ normalization/{validate.py,canonical.py,dates.py,estimates.py}
├─ graph/{build.py,cycles.py,critical_path.py}
├─ availability/{slots.py,capacity.py}
├─ scheduling/{priority.py,serial.py,passes.py}
├─ risk/{coverage.py,classify.py,external.py}
├─ replanning/{diff.py,cost.py,optimize.py}
├─ proposals/overload.py
├─ today.py
├─ evidence.py
└─ planner.py
packages/planner/tests/vectors/tv_01.json ... tv_11.json
evals/planner-vectors/reference/
```

### Task P2-T01: Validate and normalize PlannerInput deterministically

**Files:**
- Create: `packages/planner/src/personal_pm_planner/normalization/validate.py`
- Create: `packages/planner/src/personal_pm_planner/normalization/canonical.py`
- Create: `packages/planner/tests/normalization/test_validation.py`

**Interfaces:**
- Consumes: Phase 1 `PlannerInput` and canonical IDs
- Produces: `normalize_and_validate(input) -> NormalizedPlannerInput | InvalidPlannerInput`

- [x] **Step 1: Write the failing test**

```python
from dataclasses import replace
from personal_pm_planner.normalization.validate import normalize_and_validate

def test_done_task_with_remaining_minutes_is_invalid(planner_input_factory) -> None:
    value = planner_input_factory(done_task_remaining=15)
    result = normalize_and_validate(value)
    assert result.error_code == "INVALID_INPUT"
    assert "DONE_TASK_HAS_REMAINING_TIME" in result.rule_ids

def test_collection_order_does_not_change_hash(planner_input_factory) -> None:
    a = normalize_and_validate(planner_input_factory(reverse_tasks=False))
    b = normalize_and_validate(planner_input_factory(reverse_tasks=True))
    assert a.input_hash == b.input_hash
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/normalization/test_validation.py -q
```

Expected: FAIL because normalization does not exist.

- [x] **Step 3: Implement the minimum contract**

```python
def normalize_and_validate(value: PlannerInput) -> NormalizationResult:
    errors = validate_contract(value)
    if errors:
        return InvalidPlannerInput(
            error_code="INVALID_INPUT",
            rule_ids=tuple(sorted(error.rule_id for error in errors)),
            prior_plan_snapshot=value.prior_plan_snapshot,
        )
    normalized = canonicalize(value)
    return ValidPlannerInput(
        value=normalized,
        input_hash=hash_canonical_input(normalized),
    )
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/normalization/test_validation.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/normalization packages/planner/tests/contracts -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/normalization/validate.py packages/planner/src/personal_pm_planner/normalization/canonical.py packages/planner/tests/normalization/test_validation.py
git commit -m "feat(planner): normalize and validate Planner input"
```

### Task P2-T02: Implement date interpretation and estimate derivation rules

**Files:**
- Create: `packages/planner/src/personal_pm_planner/normalization/dates.py`
- Create: `packages/planner/src/personal_pm_planner/normalization/estimates.py`
- Create: `packages/planner/tests/normalization/test_dates_and_estimates.py`

**Interfaces:**
- Consumes: validated snapshots and user estimation profile
- Produces: `effective_deadline`, `adjusted_base_minutes`, `safety_minutes` with slot rounding

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner.normalization.dates import effective_deadline
from personal_pm_planner.normalization.estimates import derive_estimate

def test_date_only_deadline_uses_conservative_boundary_without_changing_fact(date_only_milestone) -> None:
    result = effective_deadline(date_only_milestone, "Asia/Seoul")
    assert result.assumption == "DATE_ONLY_START_OF_DAY"
    assert date_only_milestone.deadline_at is None

def test_high_uncertainty_uses_160_percent_and_slot_rounding() -> None:
    result = derive_estimate(raw_base_minutes=61, factor=1.0, uncertainty="high", slot_minutes=15)
    assert result.base_minutes == 75
    assert result.safety_minutes == 120
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/normalization/test_dates_and_estimates.py -q
```

Expected: FAIL because date and estimate rules are missing.

- [x] **Step 3: Implement the minimum contract**

```python
UNCERTAINTY_MULTIPLIER = {"low": 1.15, "medium": 1.35, "high": 1.60}

def ceil_to_slot(minutes: float, slot_minutes: int) -> int:
    return int(math.ceil(minutes / slot_minutes) * slot_minutes)

def derive_estimate(raw_base_minutes: int, factor: float, uncertainty: str, slot_minutes: int) -> Estimate:
    adjusted = ceil_to_slot(raw_base_minutes * min(2.50, max(0.75, factor)), slot_minutes)
    safety = ceil_to_slot(adjusted * UNCERTAINTY_MULTIPLIER[uncertainty], slot_minutes)
    return Estimate(base_minutes=adjusted, safety_minutes=max(adjusted, safety))
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/normalization/test_dates_and_estimates.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/normalization -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/normalization/dates.py packages/planner/src/personal_pm_planner/normalization/estimates.py packages/planner/tests/normalization/test_dates_and_estimates.py
git commit -m "feat(planner): derive safe dates and durations"
```

### Task P2-T03: Generate unique availability slots and reserve protected capacity

**Files:**
- Create: `packages/planner/src/personal_pm_planner/availability/slots.py`
- Create: `packages/planner/src/personal_pm_planner/availability/capacity.py`
- Create: `packages/planner/tests/availability/test_slots.py`

**Interfaces:**
- Consumes: normalized availability windows, calendar events and capacity settings
- Produces: `build_unique_slots()` with exactly one ownership state per slot

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner.availability.slots import build_unique_slots

def test_fixed_event_and_buffer_slots_are_not_free(availability_case) -> None:
    slots = build_unique_slots(availability_case)
    assert not any(slot.is_free and slot.overlaps(availability_case.fixed_event) for slot in slots)
    assert sum(slot.minutes for slot in slots if slot.state == "FREE") == availability_case.expected_planned_capacity

def test_every_slot_has_unique_id_and_one_state(availability_case) -> None:
    slots = build_unique_slots(availability_case)
    assert len({slot.id for slot in slots}) == len(slots)
    assert all(slot.state in {"FREE", "FIXED_EVENT", "PROTECTED_FOCUS_BLOCK", "BUFFER"} for slot in slots)
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/availability/test_slots.py -q
```

Expected: FAIL because slot construction is absent.

- [x] **Step 3: Implement the minimum contract**

```python
def build_unique_slots(context: AvailabilityContext) -> tuple[Slot, ...]:
    raw = split_windows(context.availability_windows, context.slot_minutes)
    marked = reserve_fixed_events(raw, context.calendar_events)
    marked = reserve_protected_focus_blocks(marked, context.prior_plan)
    marked = reserve_breaks_and_transition(marked, context.user_settings)
    return apply_daily_capacity_factor(marked, context.capacity_factor)
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/availability/test_slots.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/availability -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/availability/slots.py packages/planner/src/personal_pm_planner/availability/capacity.py packages/planner/tests/availability/test_slots.py
git commit -m "feat(planner): build unique availability slots"
```

### Task P2-T04: Build dependency graphs, cycles and latest-safe timing

**Files:**
- Create: `packages/planner/src/personal_pm_planner/graph/build.py`
- Create: `packages/planner/src/personal_pm_planner/graph/cycles.py`
- Create: `packages/planner/src/personal_pm_planner/graph/critical_path.py`
- Create: `packages/planner/tests/graph/test_dependency_timing.py`

**Interfaces:**
- Consumes: Task dependencies, effective deadlines and safety durations
- Produces: stable cycles, `must_start_by_at`, unlock counts and `latest_safe_handoff_at`

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner.graph.build import build_graph_analysis

def test_cycle_tasks_are_blocked_but_remain_in_demand(cycle_case) -> None:
    result = build_graph_analysis(cycle_case)
    assert set(result.blocked_task_ids) == set(cycle_case.task_ids)
    assert result.cycles[0].rule_id == "DEPENDENCY_CYCLE"
    assert result.required_demand_minutes > 0

def test_external_handoff_is_computed_backwards(external_dependency_case) -> None:
    result = build_graph_analysis(external_dependency_case)
    assert result.external_dependencies[0].latest_safe_handoff_at == external_dependency_case.expected_latest_safe
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/graph/test_dependency_timing.py -q
```

Expected: FAIL because graph timing is absent.

- [x] **Step 3: Implement the minimum contract**

```python
def latest_start(task_id: TaskId, graph: Graph, deadline: datetime) -> datetime:
    task = graph.tasks[task_id]
    successor_limits = [latest_start(edge.successor_id, graph, deadline) for edge in graph.start_edges_from(task_id)]
    latest_finish = min([deadline, *successor_limits])
    return latest_finish - timedelta(minutes=task.safety_duration_minutes)
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/graph/test_dependency_timing.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/graph packages/planner/tests/domain/test_dependencies.py -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/graph/build.py packages/planner/src/personal_pm_planner/graph/cycles.py packages/planner/src/personal_pm_planner/graph/critical_path.py packages/planner/tests/graph/test_dependency_timing.py
git commit -m "feat(planner): analyze dependency timing and cycles"
```

### Task P2-T05: Implement priority classes and stable tie-breaking tuple

**Files:**
- Create: `packages/planner/src/personal_pm_planner/scheduling/priority.py`
- Create: `packages/planner/tests/scheduling/test_priority.py`

**Interfaces:**
- Consumes: graph analysis, user importance and prior plan position
- Produces: `initial_priority_class`, P0 promotion and exact `priority_key` tuple

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner.scheduling.priority import priority_key

def test_identical_business_priority_uses_task_id_as_final_tie_break(priority_context, tied_tasks) -> None:
    ordered = sorted(tied_tasks, key=lambda task: priority_key(task, priority_context))
    assert [task.id.value.hex for task in ordered] == sorted(task.id.value.hex for task in tied_tasks)

def test_llm_score_is_not_part_of_key(priority_context, task_factory) -> None:
    a = task_factory(llm_score=0.01)
    b = task_factory(id=a.id, llm_score=0.99)
    assert priority_key(a, priority_context) == priority_key(b, priority_context)
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/scheduling/test_priority.py -q
```

Expected: FAIL because stable priority is not implemented.

- [x] **Step 3: Implement the minimum contract**

```python
def priority_key(task: SchedulableTask, context: PriorityContext) -> tuple[object, ...]:
    return (
        task.priority_class.rank,
        task.must_start_by_at or DATETIME_MAX_UTC,
        task.effective_deadline_at or DATETIME_MAX_UTC,
        -task.critical_path_unlock_count,
        -int(task.external_commitment),
        -task.user_importance.rank,
        task.prior_plan_position if task.prior_plan_position is not None else INT_MAX,
        task.context_switch_penalty,
        task.created_at,
        task.id.value.hex,
    )
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/scheduling/test_priority.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/scheduling -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/scheduling/priority.py packages/planner/tests/scheduling/test_priority.py
git commit -m "feat(planner): add deterministic priority ordering"
```

### Task P2-T06: Implement serial schedule generation with split and non-split tasks

**Files:**
- Create: `packages/planner/src/personal_pm_planner/scheduling/serial.py`
- Create: `packages/planner/tests/scheduling/test_serial_schedule.py`

**Interfaces:**
- Consumes: unique slots, graph readiness and stable priority
- Produces: `serial_schedule(tasks, slots, duration_field) -> ScheduleResult` without overlap

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner.scheduling.serial import serial_schedule

def test_shared_capacity_is_never_double_allocated(tv01_case) -> None:
    result = serial_schedule(**tv01_case.arguments)
    allocated_slot_ids = [slot_id for item in result.allocations for slot_id in item.source_slot_ids]
    assert len(allocated_slot_ids) == len(set(allocated_slot_ids))
    assert result.total_allocated_minutes == 240

def test_non_splittable_task_requires_contiguous_capacity(tv08_case) -> None:
    result = serial_schedule(**tv08_case.arguments)
    assert tv08_case.task_id in result.unallocated_task_ids
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/scheduling/test_serial_schedule.py -q
```

Expected: FAIL because scheduling is absent.

- [x] **Step 3: Implement the minimum contract**

```python
def serial_schedule(tasks: tuple[SchedulableTask, ...], slots: tuple[Slot, ...], duration_field: str) -> ScheduleResult:
    ledger = SlotLedger(slots)
    allocations: list[TaskAllocation] = []
    for task in sorted(tasks, key=lambda item: item.priority_key):
        required = getattr(task, duration_field)
        chosen = ledger.find_earliest_feasible(task, required)
        if chosen is None:
            continue
        ledger.allocate(task.id, chosen)
        allocations.append(TaskAllocation.from_slots(task.id, chosen, duration_field))
    return ScheduleResult.from_ledger(ledger, allocations, tasks)
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/scheduling/test_serial_schedule.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/scheduling -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/scheduling/serial.py packages/planner/tests/scheduling/test_serial_schedule.py
git commit -m "feat(planner): allocate global schedule slots"
```

### Task P2-T07: Create provisional, Base and Safety passes with synthetic buffers

**Files:**
- Create: `packages/planner/src/personal_pm_planner/scheduling/passes.py`
- Create: `packages/planner/tests/scheduling/test_passes.py`

**Interfaces:**
- Consumes: serial scheduler and milestone buffer requirements
- Produces: `run_planning_passes()` with one P0 promotion round and separate slot ledgers

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner.scheduling.passes import run_planning_passes

def test_base_and_safety_passes_use_independent_ledgers(tv09_case) -> None:
    result = run_planning_passes(tv09_case.input)
    assert result.base.total_allocated_minutes == 240
    assert result.safety.total_allocated_minutes == 300
    assert result.base.slot_ledger is not result.safety.slot_ledger

def test_synthetic_buffers_consume_real_slots(buffer_case) -> None:
    result = run_planning_passes(buffer_case.input)
    assert {item.kind for item in result.safety.allocations} >= {"REVIEW_BUFFER", "SUBMISSION_BUFFER"}
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/scheduling/test_passes.py -q
```

Expected: FAIL because planning passes are absent.

- [x] **Step 3: Implement the minimum contract**

```python
def run_planning_passes(context: PlanningContext) -> PlanningPasses:
    tasks = add_synthetic_buffers(context.tasks, context.milestones)
    provisional = serial_schedule(tasks, context.fresh_slots(), "base_duration_minutes")
    promoted = promote_infeasible_required_paths_once(tasks, provisional, context.graph)
    base = serial_schedule(promoted, context.fresh_slots(), "base_duration_minutes")
    safety = serial_schedule(promoted, context.fresh_slots(), "safety_duration_minutes")
    return PlanningPasses(provisional=provisional, base=base, safety=safety)
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/scheduling/test_passes.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/scheduling -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/scheduling/passes.py packages/planner/tests/scheduling/test_passes.py
git commit -m "feat(planner): run Base and Safety planning passes"
```

### Task P2-T08: Calculate milestone and external dependency risks from global allocations

**Files:**
- Create: `packages/planner/src/personal_pm_planner/risk/coverage.py`
- Create: `packages/planner/src/personal_pm_planner/risk/classify.py`
- Create: `packages/planner/src/personal_pm_planner/risk/external.py`
- Create: `packages/planner/tests/risk/test_risk_classification.py`

**Interfaces:**
- Consumes: Base/Safety results and graph timing
- Produces: `calculate_risks()` with definitive Critical, Unknown, capacity Critical, High, Medium and Low order

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner.risk.classify import calculate_risks

def test_base_possible_safety_impossible_is_high(tv09_case) -> None:
    risk = calculate_risks(tv09_case.passes, tv09_case.context)[tv09_case.milestone_id]
    assert risk.base_coverage == 1.0
    assert risk.safety_coverage < 1.0
    assert risk.level.value == "HIGH"

def test_date_only_current_deadline_remains_unknown(tv04_case) -> None:
    risk = calculate_risks(tv04_case.passes, tv04_case.context)[tv04_case.milestone_id]
    assert risk.level.value == "UNKNOWN"
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/risk/test_risk_classification.py -q
```

Expected: FAIL because risk classification is absent.

- [x] **Step 3: Implement the minimum contract**

```python
def classify_milestone(values: RiskInputs) -> RiskLevel:
    if values.definitive_critical:
        return RiskLevel.CRITICAL
    if values.has_unknown_required_fact:
        return RiskLevel.UNKNOWN
    if values.base_coverage < 1.0:
        return RiskLevel.CRITICAL
    if values.safety_coverage < 1.0 or not values.mandatory_buffers_allocated:
        return RiskLevel.HIGH
    if values.slack_minutes < values.medium_threshold_minutes:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/risk/test_risk_classification.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/risk packages/planner/tests/scheduling -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/risk/coverage.py packages/planner/src/personal_pm_planner/risk/classify.py packages/planner/src/personal_pm_planner/risk/external.py packages/planner/tests/risk/test_risk_classification.py
git commit -m "feat(planner): classify global capacity risks"
```

### Task P2-T09: Build today plan, minimal-change replanning and overload proposals

**Files:**
- Create: `packages/planner/src/personal_pm_planner/today.py`
- Create: `packages/planner/src/personal_pm_planner/replanning/diff.py`
- Create: `packages/planner/src/personal_pm_planner/replanning/cost.py`
- Create: `packages/planner/src/personal_pm_planner/replanning/optimize.py`
- Create: `packages/planner/src/personal_pm_planner/proposals/overload.py`
- Create: `packages/planner/tests/replanning/test_replanning.py`

**Interfaces:**
- Consumes: Base/Safety plans, risks, prior snapshot and permissions
- Produces: `build_today_plan`, lexicographic `replan`, and simulated proposal impacts

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner.replanning.optimize import replan

def test_replanning_moves_only_one_task_when_that_resolves_risk(tv10_case) -> None:
    result = replan(tv10_case.context)
    assert result.diff.changed_task_count == 1
    assert result.after.critical_count < result.before.critical_count

def test_freeze_window_change_requires_proposal(tv07_case) -> None:
    result = replan(tv07_case.context)
    assert tv07_case.frozen_task_id not in result.applied_moves
    assert result.proposals[0].approval_level.value == "APPROVAL"
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/replanning/test_replanning.py -q
```

Expected: FAIL because replanning and proposals are absent.

- [x] **Step 3: Implement the minimum contract**

```python
LEXICOGRAPHIC_FIELDS = (
    "hard_constraint_violations",
    "authorization_violations",
    "critical_milestones",
    "base_unallocated_minutes",
    "high_milestones",
    "safety_unallocated_minutes",
    "change_cost",
    "context_switches",
    "energy_mismatch",
)

def choose_candidate(candidates: tuple[ReplanCandidate, ...]) -> ReplanCandidate:
    return min(candidates, key=lambda item: tuple(getattr(item.metrics, field) for field in LEXICOGRAPHIC_FIELDS))
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/replanning/test_replanning.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests/replanning packages/planner/tests/risk -q
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/today.py packages/planner/src/personal_pm_planner/replanning/diff.py packages/planner/src/personal_pm_planner/replanning/cost.py packages/planner/src/personal_pm_planner/replanning/optimize.py packages/planner/src/personal_pm_planner/proposals/overload.py packages/planner/tests/replanning/test_replanning.py
git commit -m "feat(planner): create stable today and replan outputs"
```

### Task P2-T10: Assemble public plan function and enforce reference, property and performance gates

**Files:**
- Create: `packages/planner/src/personal_pm_planner/evidence.py`
- Create: `packages/planner/src/personal_pm_planner/planner.py`
- Modify: `packages/planner/src/personal_pm_planner/__init__.py`
- Create: `packages/planner/tests/vectors/test_reference_vectors.py`
- Create: `packages/planner/tests/properties/test_planner_invariants.py`
- Create: `packages/planner/tests/performance/test_planner_performance.py`
- Create: `evals/planner-vectors/reference/tv-01.json`
- Create: `evals/planner-vectors/reference/tv-02.json`
- Create: `evals/planner-vectors/reference/tv-03.json`
- Create: `evals/planner-vectors/reference/tv-04.json`
- Create: `evals/planner-vectors/reference/tv-05.json`
- Create: `evals/planner-vectors/reference/tv-06.json`
- Create: `evals/planner-vectors/reference/tv-07.json`
- Create: `evals/planner-vectors/reference/tv-08.json`
- Create: `evals/planner-vectors/reference/tv-09.json`
- Create: `evals/planner-vectors/reference/tv-10.json`
- Create: `evals/planner-vectors/reference/tv-11.json`

**Interfaces:**
- Consumes: all Planner modules and contracts
- Produces: `plan(input) -> PlannerOutput` plus automated PLAN/PQ evidence

- [x] **Step 1: Write the failing test**

```python
from personal_pm_planner import plan

def test_all_reference_vectors_match_expected(load_planner_vectors) -> None:
    for vector in load_planner_vectors():
        output = plan(vector.input)
        assert output.canonical_core() == vector.expected_core

def test_repeated_input_is_identical(planner_input_factory) -> None:
    value = planner_input_factory()
    cores = [plan(value).canonical_core() for _ in range(100)]
    assert len(set(cores)) == 1
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run pytest packages/planner/tests/vectors/test_reference_vectors.py -q
```

Expected: FAIL until the orchestrator and all eleven fixtures are complete.

- [x] **Step 3: Implement the minimum contract**

```python
def plan(value: PlannerInput) -> PlannerOutput:
    normalized = normalize_and_validate(value)
    if isinstance(normalized, InvalidPlannerInput):
        return PlannerOutput.invalid(normalized, planner_version=value.planner_version)
    context = build_planning_context(normalized)
    passes = run_planning_passes(context)
    risks = calculate_risks(passes, context)
    today = build_today_plan(passes, risks, context)
    candidate = replan(ReplanContext(today=today, risks=risks, planning=context))
    return build_planner_output(normalized, passes, risks, candidate)
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest packages/planner/tests/vectors/test_reference_vectors.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run pytest packages/planner/tests -q && uv run mypy packages/planner/src && uv run ruff check packages/planner
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/src/personal_pm_planner/evidence.py packages/planner/src/personal_pm_planner/planner.py packages/planner/src/personal_pm_planner/__init__.py packages/planner/tests/vectors/test_reference_vectors.py packages/planner/tests/properties/test_planner_invariants.py packages/planner/tests/performance/test_planner_performance.py evals/planner-vectors/reference/tv-01.json evals/planner-vectors/reference/tv-02.json evals/planner-vectors/reference/tv-03.json evals/planner-vectors/reference/tv-04.json evals/planner-vectors/reference/tv-05.json evals/planner-vectors/reference/tv-06.json evals/planner-vectors/reference/tv-07.json evals/planner-vectors/reference/tv-08.json evals/planner-vectors/reference/tv-09.json evals/planner-vectors/reference/tv-10.json evals/planner-vectors/reference/tv-11.json
git commit -m "feat(planner): complete normative planning engine"
```

## Phase 2 Exit Criteria

- [x] TV-01 through TV-11 pass exactly.
- [x] Same input repeated 100 times has one canonical result.
- [x] Property tests prove slot uniqueness, fixed-event exclusion, dependency order and capacity bounds.
- [x] Planner output includes version, input hash, Rule IDs, evidence, unresolved items and prior-plan diff.
- [x] Invalid input and internal failure preserve the prior valid plan.
- [x] The 500-Task benchmark harness records P50/P95 and memory.
- [x] `IMPLEMENTATION_STATUS.md` advances to Phase 3.
