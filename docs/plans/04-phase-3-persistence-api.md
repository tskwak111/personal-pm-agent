# Phase 3 — Persistence, Identity and API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist Planning Core safely in PostgreSQL, expose versioned FastAPI application services, enforce workspace ownership and optimistic concurrency, store immutable plans and transactional outbox records, and generate the TypeScript API client.

**Architecture:** SQLAlchemy adapters implement repository ports behind application services and a Unit of Work. HTTP routers contain no domain logic. Identity is represented by a server session and provider port; Google OIDC is attached in Phase 5 without changing ownership semantics.

**Tech Stack:** FastAPI, Pydantic 2, SQLAlchemy 2 async, Alembic, psycopg 3, PostgreSQL 18, Authlib-compatible identity port, pytest, pytest-asyncio and Testcontainers.

**Spec:** Design sections 7, 8, 18, 19, 21, 24 and 25; Planner output contract; SAFE-003 and PLAN-009.

## Global Constraints

- Follow `AGENTS.md` and `docs/architecture/decision-precedence.md`.
- Never weaken Planner or Evaluation gates.
- Use TDD: failing test, confirmed failure, minimum implementation, focused pass, adjacent regression, commit.
- Every state change verifies workspace ownership and expected object version.
- External behavior is represented by ports and deterministic fakes in unit tests.
- Update `docs/status/IMPLEMENTATION_STATUS.md` after every completed Task.
- Do not claim completion without fresh command output.

---

## Locked File Map

```text
apps/api/src/personal_pm_api/
├─ shared/{db.py,errors.py,unit_of_work.py,concurrency.py}
├─ identity/{models.py,repository.py,service.py,session.py,router.py}
├─ workspaces/{models.py,schemas.py,repository.py,service.py,router.py}
├─ planning/{models.py,schemas.py,repository.py,service.py,router.py}
├─ approvals/{models.py,service.py,router.py}
├─ execution/{models.py,outbox.py,repository.py}
└─ audit/{models.py,repository.py}
apps/api/migrations/
packages/api-client/
```

### Task P3-T01: Create async database settings, session and migration harness

**Files:**
- Create: `apps/api/src/personal_pm_api/shared/db.py`
- Create: `apps/api/src/personal_pm_api/shared/unit_of_work.py`
- Create: `apps/api/alembic.ini`
- Create: `apps/api/migrations/env.py`
- Create: `apps/api/tests/integration/test_database_bootstrap.py`

**Interfaces:**
- Consumes: Phase 0 settings and local PostgreSQL
- Produces: async engine/session factories, migration metadata and rollback-safe Unit of Work protocol

- [ ] **Step 1: Write the failing test**

```python
import sqlalchemy as sa
from personal_pm_api.shared.db import database_session

async def test_database_session_rolls_back_uncommitted_change(migrated_database) -> None:
    async with database_session() as session:
        await session.execute(sa.text("create temporary table rollback_probe(value int)"))
        await session.execute(sa.text("insert into rollback_probe values (1)"))
        await session.rollback()
        count = await session.scalar(sa.text("select count(*) from rollback_probe"))
        assert count == 0
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_database_bootstrap.py -q
```

Expected: FAIL because the database and migration harness are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@asynccontextmanager
async def database_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_database_bootstrap.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run alembic -c apps/api/alembic.ini upgrade head && uv run ruff check apps/api
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/shared/db.py apps/api/src/personal_pm_api/shared/unit_of_work.py apps/api/alembic.ini apps/api/migrations/env.py apps/api/tests/integration/test_database_bootstrap.py
git commit -m "feat(db): establish async persistence foundation"
```

### Task P3-T02: Create normalized Planning Core ORM models and initial migration

**Files:**
- Create: `apps/api/src/personal_pm_api/workspaces/models.py`
- Create: `apps/api/src/personal_pm_api/planning/models.py`
- Create: `apps/api/src/personal_pm_api/approvals/models.py`
- Create: `apps/api/src/personal_pm_api/execution/models.py`
- Create: `apps/api/src/personal_pm_api/audit/models.py`
- Create: `apps/api/migrations/versions/0001_planning_core.py`
- Create: `apps/api/tests/integration/test_schema_constraints.py`

**Interfaces:**
- Consumes: SQLAlchemy metadata and Phase 1 domain fields
- Produces: tables for users, workspaces, areas, workstreams, milestones, tasks, dependencies, availability, plans, proposals, approvals, audit, outbox and external executions

- [ ] **Step 1: Write the failing test**

```python
import pytest
from sqlalchemy.exc import IntegrityError

async def test_task_requires_workspace_scoped_parent(db_session, persisted_workspace) -> None:
    task = TaskModel(workspace_id=persisted_workspace.id, workstream_id=foreign_workstream_id(), title="invalid")
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()

async def test_active_external_event_id_is_unique(db_session, calendar_event_factory) -> None:
    first = calendar_event_factory(external_event_id="google-1")
    second = calendar_event_factory(external_event_id="google-1")
    db_session.add_all([first, second])
    with pytest.raises(IntegrityError):
        await db_session.flush()
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_schema_constraints.py -q
```

Expected: FAIL because the tables and constraints are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
class VersionedWorkspaceModel(Base):
    __abstract__ = True
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_schema_constraints.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run alembic -c apps/api/alembic.ini downgrade base && uv run alembic -c apps/api/alembic.ini upgrade head
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/workspaces/models.py apps/api/src/personal_pm_api/planning/models.py apps/api/src/personal_pm_api/approvals/models.py apps/api/src/personal_pm_api/execution/models.py apps/api/src/personal_pm_api/audit/models.py apps/api/migrations/versions/0001_planning_core.py apps/api/tests/integration/test_schema_constraints.py
git commit -m "feat(db): add Planning Core relational schema"
```

### Task P3-T03: Implement repository ports, adapters and Unit of Work

**Files:**
- Create: `apps/api/src/personal_pm_api/workspaces/repository.py`
- Create: `apps/api/src/personal_pm_api/planning/repository.py`
- Create: `apps/api/src/personal_pm_api/audit/repository.py`
- Modify: `apps/api/src/personal_pm_api/shared/unit_of_work.py`
- Create: `apps/api/tests/integration/test_unit_of_work.py`

**Interfaces:**
- Consumes: ORM models and domain snapshot converters
- Produces: workspace-scoped repositories and `SqlAlchemyUnitOfWork` with explicit commit

- [ ] **Step 1: Write the failing test**

```python
async def test_unit_of_work_commits_domain_and_audit_atomically(uow_factory, workspace_id) -> None:
    async with uow_factory() as uow:
        workstream = await uow.workstreams.create(workstream_command(workspace_id))
        await uow.audit.append(audit_for(workstream))
        await uow.commit()
    assert await load_workstream(workstream.id) is not None
    assert await load_audit_for(workstream.id) is not None

async def test_unit_of_work_exception_rolls_back_both(uow_factory, workspace_id) -> None:
    with pytest.raises(RuntimeError):
        async with uow_factory() as uow:
            await uow.workstreams.create(workstream_command(workspace_id))
            raise RuntimeError("abort")
    assert await count_workstreams(workspace_id) == 0
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_unit_of_work.py -q
```

Expected: FAIL because repositories and Unit of Work are missing.

- [ ] **Step 3: Implement the minimum contract**

```python
class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.workstreams = SqlAlchemyWorkstreamRepository(self.session)
        self.audit = SqlAlchemyAuditRepository(self.session)
        return self

    async def commit(self) -> None:
        await self.session.commit()

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if exc is not None:
            await self.session.rollback()
        await self.session.close()
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_unit_of_work.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_schema_constraints.py apps/api/tests/integration/test_unit_of_work.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/workspaces/repository.py apps/api/src/personal_pm_api/planning/repository.py apps/api/src/personal_pm_api/audit/repository.py apps/api/src/personal_pm_api/shared/unit_of_work.py apps/api/tests/integration/test_unit_of_work.py
git commit -m "feat(db): add repositories and unit of work"
```

### Task P3-T04: Implement identity session, workspace ownership and test provider

**Files:**
- Create: `apps/api/src/personal_pm_api/identity/models.py`
- Create: `apps/api/src/personal_pm_api/identity/repository.py`
- Create: `apps/api/src/personal_pm_api/identity/service.py`
- Create: `apps/api/src/personal_pm_api/identity/session.py`
- Create: `apps/api/src/personal_pm_api/identity/router.py`
- Create: `apps/api/tests/integration/test_identity_and_ownership.py`

**Interfaces:**
- Consumes: users/workspaces schema and FastAPI dependency injection
- Produces: `CurrentActor`, signed server session, test identity provider and ownership guard

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

def test_cross_workspace_object_is_not_disclosed(client_as_user_a, user_b_task) -> None:
    response = client_as_user_a.get(f"/api/v1/tasks/{user_b_task.id}")
    assert response.status_code == 404

def test_missing_session_is_unauthorized(client: TestClient) -> None:
    response = client.get("/api/v1/workstreams")
    assert response.status_code == 401
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_identity_and_ownership.py -q
```

Expected: FAIL because identity and ownership guards are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
@dataclass(frozen=True, slots=True)
class CurrentActor:
    user_id: UUID
    workspace_id: UUID
    session_id: UUID

async def require_owned_object(repository: WorkspaceScopedRepository[T], actor: CurrentActor, object_id: UUID) -> T:
    value = await repository.get(actor.workspace_id, object_id)
    if value is None:
        raise NotFoundError()
    return value
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_identity_and_ownership.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/identity/models.py apps/api/src/personal_pm_api/identity/repository.py apps/api/src/personal_pm_api/identity/service.py apps/api/src/personal_pm_api/identity/session.py apps/api/src/personal_pm_api/identity/router.py apps/api/tests/integration/test_identity_and_ownership.py
git commit -m "feat(identity): enforce workspace ownership"
```

### Task P3-T05: Enforce optimistic concurrency and idempotent command envelopes

**Files:**
- Create: `apps/api/src/personal_pm_api/shared/concurrency.py`
- Create: `apps/api/src/personal_pm_api/shared/idempotency.py`
- Create: `apps/api/tests/integration/test_concurrency.py`

**Interfaces:**
- Consumes: versioned ORM models and actor context
- Produces: `ExpectedVersion`, stale-write conflict and command idempotency records

- [ ] **Step 1: Write the failing test**

```python
async def test_stale_task_update_returns_conflict(auth_client, persisted_task) -> None:
    first = auth_client.patch(f"/api/v1/tasks/{persisted_task.id}", json={"expected_version": 1, "title": "first"})
    second = auth_client.patch(f"/api/v1/tasks/{persisted_task.id}", json={"expected_version": 1, "title": "second"})
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["code"] == "STALE_OBJECT_VERSION"
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_concurrency.py -q
```

Expected: FAIL because stale writes are currently accepted or endpoint is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
async def update_with_version(session: AsyncSession, model: type[M], object_id: UUID, expected_version: int, values: dict[str, object]) -> M:
    statement = (
        update(model)
        .where(model.id == object_id, model.version == expected_version)
        .values(**values, version=model.version + 1)
        .returning(model)
    )
    updated = (await session.execute(statement)).scalar_one_or_none()
    if updated is None:
        raise StaleObjectVersionError(object_id, expected_version)
    return updated
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_concurrency.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_identity_and_ownership.py apps/api/tests/integration/test_concurrency.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/shared/concurrency.py apps/api/src/personal_pm_api/shared/idempotency.py apps/api/tests/integration/test_concurrency.py
git commit -m "feat(api): enforce optimistic concurrency"
```

### Task P3-T06: Implement workspace, milestone, task and dependency application services

**Files:**
- Create: `apps/api/src/personal_pm_api/workspaces/schemas.py`
- Create: `apps/api/src/personal_pm_api/workspaces/service.py`
- Create: `apps/api/src/personal_pm_api/workspaces/router.py`
- Create: `apps/api/tests/integration/test_workspace_api.py`

**Interfaces:**
- Consumes: repositories, actor, state machine and authorization policy
- Produces: versioned CRUD/command endpoints that emit Audit Events

- [ ] **Step 1: Write the failing test**

```python
def test_task_completion_uses_domain_state_machine(auth_client, ready_task) -> None:
    response = auth_client.post(
        f"/api/v1/tasks/{ready_task.id}/transition",
        json={"expected_version": ready_task.version, "target_status": "DONE", "completion_confirmed": True},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "TASK_HAS_REMAINING_TIME"

def test_hard_deadline_change_creates_proposal(auth_client, hard_deadline_milestone) -> None:
    response = auth_client.patch(
        f"/api/v1/milestones/{hard_deadline_milestone.id}",
        json={"expected_version": 1, "deadline_date": "2026-09-11"},
    )
    assert response.status_code == 202
    assert response.json()["proposal"]["authorization_level"] == "RECONFIRM"
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_workspace_api.py -q
```

Expected: FAIL because application commands and endpoints are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
@router.post("/tasks/{task_id}/transition", response_model=TaskResponse)
async def transition_task_endpoint(task_id: UUID, request: TaskTransitionRequest, actor: CurrentActor = Depends(current_actor), service: WorkspaceService = Depends(workspace_service)) -> TaskResponse:
    result = await service.transition_task(actor, task_id, request)
    return TaskResponse.from_domain(result)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_workspace_api.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration -q && uv run mypy apps/api/src
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/workspaces/schemas.py apps/api/src/personal_pm_api/workspaces/service.py apps/api/src/personal_pm_api/workspaces/router.py apps/api/tests/integration/test_workspace_api.py
git commit -m "feat(api): expose Planning Core commands"
```

### Task P3-T07: Persist immutable Plan Snapshots and call the pure Planner

**Files:**
- Create: `apps/api/src/personal_pm_api/planning/schemas.py`
- Create: `apps/api/src/personal_pm_api/planning/service.py`
- Create: `apps/api/src/personal_pm_api/planning/router.py`
- Create: `apps/api/tests/integration/test_planning_service.py`

**Interfaces:**
- Consumes: Planner package, repositories and actor context
- Produces: `PlanningService.create_plan()` that snapshots input/output and preserves last valid plan

- [ ] **Step 1: Write the failing test**

```python
async def test_failed_planner_does_not_replace_last_valid_plan(planning_service, workspace_with_valid_plan, invalid_plan_request) -> None:
    before = await planning_service.latest_valid(workspace_with_valid_plan.id)
    result = await planning_service.create_plan(workspace_with_valid_plan.actor, invalid_plan_request)
    after = await planning_service.latest_valid(workspace_with_valid_plan.id)
    assert result.status == "INVALID_INPUT"
    assert after.id == before.id

async def test_plan_snapshot_stores_input_hash_and_version(planning_service, normal_workspace) -> None:
    result = await planning_service.create_plan(normal_workspace.actor, CreatePlanRequest(reason="manual"))
    assert result.planner_version == "1.0"
    assert len(result.input_hash) == 64
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_planning_service.py -q
```

Expected: FAIL because PlanningService and snapshot persistence are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
class PlanningService:
    async def create_plan(self, actor: CurrentActor, request: CreatePlanRequest) -> PlanSnapshotDTO:
        async with self.uow_factory() as uow:
            planner_input = await self.snapshot_builder.build(uow, actor.workspace_id, request)
            output = self.planner(planner_input)
            snapshot = await uow.plans.append(actor.workspace_id, planner_input, output, request.reason)
            await uow.audit.append(AuditEvent.for_plan(snapshot, actor.user_id))
            await uow.commit()
            return PlanSnapshotDTO.from_record(snapshot)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_planning_service.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration packages/planner/tests -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/planning/schemas.py apps/api/src/personal_pm_api/planning/service.py apps/api/src/personal_pm_api/planning/router.py apps/api/tests/integration/test_planning_service.py
git commit -m "feat(planning): persist immutable Planner snapshots"
```

### Task P3-T08: Implement transactional outbox and external execution records

**Files:**
- Create: `apps/api/src/personal_pm_api/execution/outbox.py`
- Create: `apps/api/src/personal_pm_api/execution/repository.py`
- Create: `apps/api/tests/integration/test_outbox_atomicity.py`

**Interfaces:**
- Consumes: Unit of Work and execution tables
- Produces: `enqueue_external_command()` that commits state and outbox atomically

- [ ] **Step 1: Write the failing test**

```python
async def test_state_change_and_outbox_are_atomic(uow_factory, focus_block_command) -> None:
    with pytest.raises(RuntimeError):
        async with uow_factory() as uow:
            await enqueue_external_command(uow, focus_block_command)
            raise RuntimeError("crash before commit")
    assert await count_focus_blocks() == 0
    assert await count_outbox_events() == 0

async def test_idempotency_key_is_unique(db_session, focus_block_command) -> None:
    await insert_outbox(db_session, focus_block_command)
    with pytest.raises(IntegrityError):
        await insert_outbox(db_session, focus_block_command)
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_outbox_atomicity.py -q
```

Expected: FAIL because outbox command persistence is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
async def enqueue_external_command(uow: SqlAlchemyUnitOfWork, command: ExternalCommand) -> OutboxRecord:
    await uow.external_state.apply_pending(command)
    record = await uow.outbox.create(
        workspace_id=command.workspace_id,
        operation_id=command.operation_id,
        idempotency_key=command.idempotency_key,
        command_type=command.command_type,
        payload=command.canonical_payload,
    )
    return record
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_outbox_atomicity.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/execution/outbox.py apps/api/src/personal_pm_api/execution/repository.py apps/api/tests/integration/test_outbox_atomicity.py
git commit -m "feat(execution): add transactional outbox records"
```

### Task P3-T09: Generate and verify the TypeScript OpenAPI client

**Files:**
- Create: `packages/api-client/package.json`
- Create: `packages/api-client/openapi.config.mjs`
- Create: `packages/api-client/src/index.ts`
- Create: `scripts/export_openapi.py`
- Create: `apps/api/tests/contract/test_openapi.py`
- Create: `packages/api-client/src/generated/.gitkeep`

**Interfaces:**
- Consumes: FastAPI application schemas and pnpm workspace
- Produces: stable OpenAPI JSON and generated typed client consumed by the web app

- [ ] **Step 1: Write the failing test**

```python
from personal_pm_api.main import create_app

def test_openapi_has_versioned_core_resources() -> None:
    paths = create_app().openapi()["paths"]
    assert "/api/v1/tasks/{task_id}/transition" in paths
    assert "/api/v1/plans" in paths
    assert "/api/v1/proposals/{proposal_id}/approve" in paths
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/contract/test_openapi.py -q
```

Expected: FAIL until the API routes and export script are registered.

- [ ] **Step 3: Implement the minimum contract**

```python
# packages/api-client/openapi.config.mjs
export default {
  input: "../../artifacts/openapi.json",
  output: "src/generated/schema.ts",
  client: "fetch",
};
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/contract/test_openapi.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run python scripts/export_openapi.py && pnpm --filter @personal-pm/api-client generate && pnpm --filter @personal-pm/api-client typecheck
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add packages/api-client/package.json packages/api-client/openapi.config.mjs packages/api-client/src/index.ts scripts/export_openapi.py apps/api/tests/contract/test_openapi.py packages/api-client/src/generated/.gitkeep
git commit -m "feat(api): publish generated TypeScript client"
```

## Phase 3 Exit Criteria

- [ ] Blank database and previous migration state both upgrade successfully.
- [ ] Workspace ownership returns no cross-tenant information.
- [ ] Stale object versions return typed conflict without overwrite.
- [ ] Domain state and Audit Event commit atomically.
- [ ] Valid plans append immutable snapshots; invalid plans preserve the last valid snapshot.
- [ ] State plus outbox commit atomically and duplicate idempotency keys are rejected.
- [ ] OpenAPI and generated TypeScript client are reproducible.
