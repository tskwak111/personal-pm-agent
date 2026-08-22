# Phase 6 — Agent Orchestration, Approval, Briefing and Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn domain, Planner, intake and external adapters into an explicit Observe→Interpret→Retrieve→Plan→Critique→Authorize→Act→Verify→Explain→Learn operation flow with approvals, work sessions, briefings, notifications and streaming status.

**Architecture:** Every user request creates an `AgentOperation` with typed steps and immutable events. The orchestrator invokes application services, never repositories or provider SDKs directly. Briefing and explanation generators consume verified Planner evidence; approvals and notifications are deterministic policies.

**Tech Stack:** FastAPI application services, Pydantic operations, LLM Gateway, Redis jobs, PostgreSQL operation/audit tables, SSE, pytest and deterministic fakes.

**Spec:** Design sections 6, 7, 14, 15, 17 and 27; Planner `DecisionEvidence`; Evaluation authority and UX gates.

## Global Constraints

- Follow `AGENTS.md`, the approved specs and exact Phase interface contracts.
- LLMs generate candidates and language; deterministic services authorize and execute.
- User-facing state must distinguish fact, inference, proposal, internal execution and external execution.
- Use TDD and fresh verification before every completion claim.
- Update implementation status and traceability after every Task.

---

## Locked File Map

```text
apps/api/src/personal_pm_api/agent/
├─ models.py
├─ schemas.py
├─ intent.py
├─ context.py
├─ orchestrator.py
├─ operations.py
├─ explanations.py
└─ router.py
apps/api/src/personal_pm_api/approvals/
apps/api/src/personal_pm_api/analytics/
apps/api/src/personal_pm_api/notifications/
apps/worker/src/personal_pm_worker/briefings/
```

### Task P6-T01: Persist typed Agent Operations and step events

**Files:**
- Create: `apps/api/src/personal_pm_api/agent/models.py`
- Create: `apps/api/src/personal_pm_api/agent/schemas.py`
- Create: `apps/api/src/personal_pm_api/agent/operations.py`
- Create: `apps/api/tests/integration/test_agent_operations.py`

**Interfaces:**
- Consumes: workspace ownership, audit and optimistic concurrency
- Produces: `AgentOperation` and append-only `OperationStepEvent` lifecycle with stable operation IDs

- [ ] **Step 1: Write the failing test**

```python
async def test_operation_steps_are_append_only(operation_service, actor) -> None:
    operation = await operation_service.start(actor, "오늘 일정 다시 짜줘")
    await operation_service.append_step(operation.id, "OBSERVE", "SUCCEEDED")
    await operation_service.append_step(operation.id, "PLAN", "SUCCEEDED")
    events = await operation_service.events(actor, operation.id)
    assert [event.step for event in events] == ["OBSERVE", "PLAN"]

async def test_cross_workspace_operation_is_hidden(client_as_user_a, user_b_operation) -> None:
    response = client_as_user_a.get(f"/api/v1/agent/operations/{user_b_operation.id}")
    assert response.status_code == 404
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_agent_operations.py -q
```

Expected: FAIL because operation persistence is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
OPERATION_STEPS = (
    "OBSERVE", "INTERPRET", "RETRIEVE", "PLAN", "CRITIQUE",
    "AUTHORIZE", "ACT", "VERIFY", "EXPLAIN", "LEARN",
)

async def append_step(self, operation_id: UUID, step: str, status: str, payload: dict[str, object] | None = None) -> OperationStepEvent:
    if step not in OPERATION_STEPS:
        raise InvalidOperationStepError(step)
    return await self.repository.append_event(operation_id, step, status, payload or {})
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_agent_operations.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_identity_and_ownership.py apps/api/tests/integration/test_agent_operations.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/agent/models.py apps/api/src/personal_pm_api/agent/schemas.py apps/api/src/personal_pm_api/agent/operations.py apps/api/tests/integration/test_agent_operations.py
git commit -m "feat(agent): persist operation step events"
```

### Task P6-T02: Classify user intent without executing ambiguous language

**Files:**
- Create: `apps/api/src/personal_pm_api/agent/intent.py`
- Create: `apps/api/tests/unit/test_intent_classification.py`

**Interfaces:**
- Consumes: LLM structured candidate and deterministic command grammar
- Produces: `IntentResult` separating Question, Add Input, Change Command, Approval and Ambiguous Review

- [ ] **Step 1: Write the failing test**

```python
from personal_pm_api.agent.intent import classify_intent

def test_conditional_language_is_review_not_command() -> None:
    result = classify_intent("논문 정리를 다음 주로 미루면 어떨까?")
    assert result.kind == "REVIEW_REQUEST"
    assert result.may_mutate is False

def test_direct_imperative_is_change_command() -> None:
    result = classify_intent("논문 정리를 다음 주로 미뤄")
    assert result.kind == "CHANGE_COMMAND"
    assert result.may_mutate is True
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/unit/test_intent_classification.py -q
```

Expected: FAIL because intent policy is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
REVIEW_MARKERS = ("어떨까", "하면 좋을까", "가능할까", "검토해")
COMMAND_MARKERS = ("추가해", "미뤄", "변경해", "완료해", "시작해")

def classify_intent(text: str) -> IntentResult:
    normalized = text.strip()
    if any(marker in normalized for marker in REVIEW_MARKERS):
        return IntentResult(kind="REVIEW_REQUEST", may_mutate=False)
    if any(marker in normalized for marker in COMMAND_MARKERS):
        return IntentResult(kind="CHANGE_COMMAND", may_mutate=True)
    return IntentResult(kind="AMBIGUOUS", may_mutate=False)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/unit/test_intent_classification.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/unit/test_intent_classification.py apps/worker/tests/llm/test_gateway_contract.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/agent/intent.py apps/api/tests/unit/test_intent_classification.py
git commit -m "feat(agent): classify safe command intent"
```

### Task P6-T03: Build least-context verified Context Builder

**Files:**
- Create: `apps/api/src/personal_pm_api/agent/context.py`
- Create: `apps/api/tests/unit/test_context_builder.py`

**Interfaces:**
- Consumes: Planning repositories, actor, intent and source references
- Produces: request-specific context with `SYSTEM_POLICY`, `VERIFIED_FACTS`, `USER_REQUEST`, `UNTRUSTED_SOURCE_CONTENT`, `OUTPUT_SCHEMA`

- [ ] **Step 1: Write the failing test**

```python
async def test_today_replan_context_excludes_unrelated_project_documents(context_builder, replan_request) -> None:
    context = await context_builder.build(replan_request)
    assert context.verified_facts.today_availability is not None
    assert all(source.workstream_id in replan_request.relevant_workstream_ids for source in context.untrusted_sources)

def test_untrusted_content_cannot_enter_verified_facts(context_builder, malicious_source_request) -> None:
    context = context_builder.build_sync(malicious_source_request)
    assert "ignore previous instructions" not in context.verified_facts.rendered
    assert "ignore previous instructions" in context.untrusted_source_content
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/unit/test_context_builder.py -q
```

Expected: FAIL because the Context Builder is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
@dataclass(frozen=True, slots=True)
class AgentContext:
    system_policy: SystemPolicy
    verified_facts: VerifiedFactBundle
    user_request: str
    untrusted_source_content: tuple[SourceChunk, ...]
    output_schema_name: str
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/unit/test_context_builder.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/unit/test_context_builder.py apps/api/tests/integration/test_planning_service.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/agent/context.py apps/api/tests/unit/test_context_builder.py
git commit -m "feat(agent): build minimal verified context"
```

### Task P6-T04: Implement Orchestrator flow and rule-based Risk Reviewer

**Files:**
- Create: `apps/api/src/personal_pm_api/agent/orchestrator.py`
- Create: `apps/api/src/personal_pm_api/agent/explanations.py`
- Create: `apps/api/tests/integration/test_orchestrator_flow.py`

**Interfaces:**
- Consumes: operations, intent, context, Planner service, intake, authorization and execution services
- Produces: ordered operation flow that cannot Act before Authorize and Verify

- [ ] **Step 1: Write the failing test**

```python
async def test_mutating_operation_cannot_act_before_authorization(orchestrator, focus_block_request) -> None:
    result = await orchestrator.handle(focus_block_request)
    steps = [event.step for event in result.events]
    assert steps.index("AUTHORIZE") < steps.index("ACT")
    assert result.authorization.level == "APPROVAL"
    assert result.external_action_executed is False

async def test_failed_external_verification_is_reported_as_failed(orchestrator, failing_execution_request) -> None:
    result = await orchestrator.handle(failing_execution_request)
    assert result.status == "FAILED"
    assert result.user_message.code == "EXTERNAL_EXECUTION_FAILED"
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_orchestrator_flow.py -q
```

Expected: FAIL because the orchestrator is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
class AgentOrchestrator:
    async def handle(self, request: AgentRequest) -> AgentOperationResult:
        operation = await self.operations.start(request.actor, request.text)
        observed = await self.observe(request, operation)
        interpreted = await self.interpret(observed, operation)
        retrieved = await self.retrieve(interpreted, operation)
        planned = await self.plan(retrieved, operation)
        critiqued = self.risk_reviewer.review(planned)
        authorized = self.authorization.authorize(critiqued)
        acted = await self.act_if_allowed(authorized, operation)
        verified = await self.verify(acted, operation)
        return await self.explain_and_learn(verified, operation)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_orchestrator_flow.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_orchestrator_flow.py apps/api/tests/integration/test_focus_block_approval.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/agent/orchestrator.py apps/api/src/personal_pm_api/agent/explanations.py apps/api/tests/integration/test_orchestrator_flow.py
git commit -m "feat(agent): orchestrate authorized operations"
```

### Task P6-T05: Complete Proposal approval, rejection, supersession and undo contracts

**Files:**
- Create: `apps/api/src/personal_pm_api/approvals/service.py`
- Create: `apps/api/src/personal_pm_api/approvals/router.py`
- Create: `apps/api/tests/integration/test_approval_service.py`

**Interfaces:**
- Consumes: Proposal records, object versions, authorization policy and application commands
- Produces: version-bound approve/reject/modify/undo behavior with explicit reversibility

- [ ] **Step 1: Write the failing test**

```python
async def test_approval_executes_exact_proposed_change(approval_service, proposal) -> None:
    result = await approval_service.approve(proposal.actor, proposal.id, proposal.version)
    assert result.executed_change == proposal.proposed_change
    assert result.status == "EXECUTED"

async def test_changed_target_supersedes_old_proposal(approval_service, proposal, mutate_target) -> None:
    await mutate_target(proposal.target_id)
    result = await approval_service.approve(proposal.actor, proposal.id, proposal.version)
    assert result.status == "SUPERSEDED"
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_approval_service.py -q
```

Expected: FAIL because approval execution is incomplete.

- [ ] **Step 3: Implement the minimum contract**

```python
async def approve(self, actor: CurrentActor, proposal_id: UUID, expected_version: int) -> ApprovalResult:
    proposal = await self.repository.get_owned(actor.workspace_id, proposal_id)
    require_version(proposal, expected_version)
    target = await self.targets.load(actor.workspace_id, proposal.target_type, proposal.target_id)
    if target.version != proposal.target_version:
        return await self.supersede(proposal, "TARGET_VERSION_CHANGED")
    result = await self.commands.execute_exact(actor, proposal.proposed_change)
    return await self.mark_executed(proposal, result)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_approval_service.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_approval_service.py apps/api/tests/integration/test_concurrency.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/approvals/service.py apps/api/src/personal_pm_api/approvals/router.py apps/api/tests/integration/test_approval_service.py
git commit -m "feat(approvals): enforce version-bound decisions"
```

### Task P6-T06: Implement Work Session and estimation analytics

**Files:**
- Create: `apps/api/src/personal_pm_api/analytics/models.py`
- Create: `apps/api/src/personal_pm_api/analytics/service.py`
- Create: `apps/api/src/personal_pm_api/analytics/router.py`
- Create: `apps/api/tests/integration/test_work_sessions.py`

**Interfaces:**
- Consumes: Task state machine, plan allocations and estimation profiles
- Produces: start/extend/partial/complete/block session operations and bounded profile factor updates

- [ ] **Step 1: Write the failing test**

```python
async def test_partial_completion_records_actual_and_remaining_time(session_service, ready_task, fake_clock) -> None:
    session = await session_service.start(ready_task.actor, ready_task.id)
    fake_clock.advance(minutes=75)
    result = await session_service.partial_complete(ready_task.actor, session.id, remaining_base_minutes=50)
    assert result.actual_focus_minutes == 75
    assert result.task.remaining_base_minutes == 50

async def test_two_samples_do_not_change_estimation_factor(profile_service, two_completed_sessions) -> None:
    profile = await profile_service.recalculate(two_completed_sessions.workspace_id, "backend")
    assert profile.factor == 1.0
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_work_sessions.py -q
```

Expected: FAIL because Work Sessions and profile updates are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
def blended_factor(observed_ratio: float, sample_count: int) -> float:
    weight = 0.0 if sample_count <= 2 else 0.30 if sample_count <= 5 else 0.60 if sample_count <= 19 else 0.80
    return min(2.50, max(0.75, 1.0 + (observed_ratio - 1.0) * weight))
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_work_sessions.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_work_sessions.py packages/planner/tests/normalization/test_dates_and_estimates.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/analytics/models.py apps/api/src/personal_pm_api/analytics/service.py apps/api/src/personal_pm_api/analytics/router.py apps/api/tests/integration/test_work_sessions.py
git commit -m "feat(analytics): track sessions and estimates"
```

### Task P6-T07: Generate evidence-grounded morning, evening and weekly briefings

**Files:**
- Create: `apps/worker/src/personal_pm_worker/briefings/generator.py`
- Create: `apps/worker/src/personal_pm_worker/briefings/schemas.py`
- Create: `apps/worker/tests/briefings/test_briefing_grounding.py`

**Interfaces:**
- Consumes: latest valid Plan Snapshot, Work Sessions, risks and LLM Gateway
- Produces: structured briefing payload and language that cannot add unsupported reasons

- [ ] **Step 1: Write the failing test**

```python
async def test_briefing_contains_only_planner_rule_ids(generator, briefing_context) -> None:
    result = await generator.generate_morning(briefing_context)
    assert set(result.reason_rule_ids) <= set(briefing_context.decision_evidence.planner_rule_ids)

async def test_evening_copy_is_nonjudgmental(generator, missed_plan_context) -> None:
    result = await generator.generate_evening(missed_plan_context)
    forbidden = {"실패", "게으름", "생산성이 낮"}
    assert not any(word in result.rendered_text for word in forbidden)
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/worker/tests/briefings/test_briefing_grounding.py -q
```

Expected: FAIL because grounded briefing generation is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
@dataclass(frozen=True, slots=True)
class MorningBriefing:
    available_minutes: int
    fixed_events: tuple[BriefingEvent, ...]
    core_outcome: str
    must_do: tuple[BriefingTask, ...]
    risk_cards: tuple[BriefingRisk, ...]
    decision_requests: tuple[BriefingProposal, ...]
    reason_rule_ids: tuple[str, ...]
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/worker/tests/briefings/test_briefing_grounding.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/worker/tests/briefings apps/worker/tests/llm -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/worker/src/personal_pm_worker/briefings/generator.py apps/worker/src/personal_pm_worker/briefings/schemas.py apps/worker/tests/briefings/test_briefing_grounding.py
git commit -m "feat(briefings): generate grounded daily reviews"
```

### Task P6-T08: Implement notification intents, deduplication, quiet hours and SSE operation streams

**Files:**
- Create: `apps/api/src/personal_pm_api/notifications/models.py`
- Create: `apps/api/src/personal_pm_api/notifications/policy.py`
- Create: `apps/api/src/personal_pm_api/notifications/service.py`
- Create: `apps/api/src/personal_pm_api/agent/router.py`
- Create: `apps/api/tests/integration/test_notifications_and_sse.py`

**Interfaces:**
- Consumes: briefing payload, operation events, user notification settings and Redis
- Produces: Critical/Actionable/Summary/Silent delivery policy and resumable SSE event stream

- [ ] **Step 1: Write the failing test**

```python
async def test_same_risk_is_deduplicated(notification_service, risk_intent) -> None:
    first = await notification_service.enqueue(risk_intent)
    second = await notification_service.enqueue(risk_intent)
    assert second.id == first.id
    assert await pending_notification_count(risk_intent.dedupe_key) == 1

async def test_sse_replays_after_last_event_id(auth_client, operation_events) -> None:
    response = auth_client.get(f"/api/v1/agent/operations/{operation_events.operation_id}/stream", headers={"Last-Event-ID": str(operation_events.first.id)})
    assert str(operation_events.first.id) not in response.text
    assert str(operation_events.second.id) in response.text
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_notifications_and_sse.py -q
```

Expected: FAIL because notification policy and SSE replay are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
def delivery_mode(intent: NotificationIntent, settings: NotificationSettings, now: datetime) -> DeliveryMode:
    if intent.severity is NotificationSeverity.SILENT:
        return DeliveryMode.RECORD_ONLY
    if settings.is_quiet(now) and intent.severity is not NotificationSeverity.CRITICAL:
        return DeliveryMode.NEXT_SUMMARY
    if intent.severity is NotificationSeverity.SUMMARY:
        return DeliveryMode.NEXT_SUMMARY
    return DeliveryMode.IMMEDIATE
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_notifications_and_sse.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_orchestrator_flow.py apps/api/tests/integration/test_notifications_and_sse.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/notifications/models.py apps/api/src/personal_pm_api/notifications/policy.py apps/api/src/personal_pm_api/notifications/service.py apps/api/src/personal_pm_api/agent/router.py apps/api/tests/integration/test_notifications_and_sse.py
git commit -m "feat(agent): stream operations and dedupe notifications"
```

## Phase 6 Exit Criteria

- [ ] Agent Operations have an auditable ordered step history.
- [ ] Ambiguous review language cannot execute a change.
- [ ] Orchestrator cannot Act before authorization or report success before verification.
- [ ] Approval is bound to proposal and target versions.
- [ ] Work Session and estimation updates follow sample-count rules.
- [ ] Briefing reasons are a subset of verified Planner evidence.
- [ ] Notification dedupe, quiet hours and SSE replay have tests.
