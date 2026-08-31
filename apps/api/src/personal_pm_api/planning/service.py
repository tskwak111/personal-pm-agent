"""Immutable plan snapshots backed by the pure planner.

A failed normalization or planning run NEVER replaces the last validated
current snapshot (PLAN-009); only fully valid outputs append history.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from personal_pm_planner.contracts.input import (
    PlannerInput,
    PriorAllocation,
    PriorPlanSnapshot,
)
from personal_pm_planner.contracts.output import PlannerOutput
from personal_pm_planner.domain.availability import (
    AvailabilityWindow,
    CalendarEventSnapshot,
    ExternalDependencySnapshot,
)
from personal_pm_planner.domain.dependency import TaskDependency
from personal_pm_planner.domain.enums import (
    CalendarEventKind,
    DeadlineType,
    DependencyType,
    TaskStatus,
    Uncertainty,
)
from personal_pm_planner.domain.identifiers import (
    CalendarEventId,
    ExternalDependencyId,
    MilestoneId,
    TaskId,
    WorkspaceId,
    WorkstreamId,
)
from personal_pm_planner.domain.task import TaskSnapshot
from personal_pm_planner.domain.time import require_aware_utc
from personal_pm_planner.domain.work import MilestoneSnapshot
from personal_pm_planner.normalization.validate import normalize_and_validate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Full registry import: ORM FK resolution needs every mapped table loaded.
from personal_pm_api.approvals import models as _approvals_m  # noqa: F401
from personal_pm_api.audit import models as _audit_m  # noqa: F401
from personal_pm_api.execution import models as _execution_m  # noqa: F401
from personal_pm_api.identity import models as _identity_m  # noqa: F401
from personal_pm_api.planning.models import (
    AvailabilityWindowModel,
    CalendarEventModel,
    ExternalDependencyModel,
    ExternalDependencyTaskModel,
    MilestoneModel,
    PlanSnapshotModel,
    TaskDependencyModel,
    TaskModel,
    WorkspaceExcludedDateModel,
)
from personal_pm_api.planning.repository import PlanningRepository
from personal_pm_api.planning.schemas import PlanSnapshotDTO
from personal_pm_api.telemetry.metrics import RUNTIME_METRICS
from personal_pm_api.workspaces.models import WorkspaceModel

PLANNER_VERSION = "planner-spec-1.0"


def _task_snapshot_from_model(model: TaskModel) -> TaskSnapshot:
    return TaskSnapshot(
        id=TaskId(model.id),
        workspace_id=WorkspaceId(model.workspace_id),
        workstream_id=WorkstreamId(model.workstream_id),
        milestone_id=MilestoneId(model.milestone_id) if model.milestone_id else None,
        title=model.title,
        status=TaskStatus(model.status),
        deadline_date=model.deadline_date,
        deadline_at=model.deadline_at,
        deadline_time_known=model.deadline_time_known,
        start_after=model.start_after,
        base_duration_minutes=model.base_duration_minutes,
        safety_duration_minutes=model.safety_duration_minutes,
        remaining_base_minutes=model.remaining_base_minutes,
        remaining_safety_minutes=model.remaining_safety_minutes,
        uncertainty=Uncertainty(model.uncertainty),
        splittable=model.splittable,
        min_chunk_minutes=model.min_chunk_minutes,
        pinned=model.pinned,
        waiting_reason=model.waiting_reason,
        version=model.version,
    )


def _milestone_snapshot_from_model(model: MilestoneModel) -> MilestoneSnapshot:
    return MilestoneSnapshot(
        id=MilestoneId(model.id),
        workspace_id=WorkspaceId(model.workspace_id),
        workstream_id=WorkstreamId(model.workstream_id),
        title=model.title,
        deadline_date=model.deadline_date,
        deadline_at=model.deadline_at,
        deadline_date_known=model.deadline_date_known,
        deadline_time_known=model.deadline_time_known,
        deadline_type=DeadlineType(model.deadline_type),
        required_buffer_minutes=model.required_buffer_minutes,
        version=model.version,
    )


def _calendar_snapshot_from_model(model: CalendarEventModel) -> CalendarEventSnapshot:
    return CalendarEventSnapshot(
        id=CalendarEventId(model.id),
        workspace_id=WorkspaceId(model.workspace_id),
        title=model.title,
        start_at=model.start_at,
        end_at=model.end_at,
        event_kind=CalendarEventKind(model.event_kind),
        deadline_date=model.deadline_date,
        version=model.version,
    )


def _prior_snapshot_from_model(model: PlanSnapshotModel) -> PriorPlanSnapshot:
    raw_allocations = model.output_json.get("base_allocations")
    if not isinstance(raw_allocations, list):
        raise ValueError("prior plan is missing base_allocations")
    allocations: list[PriorAllocation] = []
    for raw in raw_allocations:
        if not isinstance(raw, dict):
            raise ValueError("prior plan allocation must be an object")
        task_id = raw.get("task_id")
        start_text = raw.get("start")
        end_text = raw.get("end")
        if not all(isinstance(item, str) for item in (task_id, start_text, end_text)):
            raise ValueError("prior plan allocation fields must be strings")
        assert isinstance(task_id, str)
        assert isinstance(start_text, str)
        assert isinstance(end_text, str)
        start_at = require_aware_utc(datetime.fromisoformat(start_text))
        end_at = require_aware_utc(datetime.fromisoformat(end_text))
        if end_at <= start_at:
            raise ValueError("prior plan allocation end must be after start")
        allocations.append(
            PriorAllocation(
                task_id=TaskId(UUID(hex=task_id)),
                start_at=start_at,
                end_at=end_at,
            )
        )
    return PriorPlanSnapshot(
        id=model.id,
        input_hash=model.input_hash,
        allocations=tuple(allocations),
    )


class PlanningService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _build_planner_input(self, workspace_id: UUID, now_utc: datetime) -> PlannerInput:
        workspace = await self._session.get(WorkspaceModel, workspace_id)
        if workspace is None:
            raise ValueError("workspace not found")

        window_rows = list(
            (
                await self._session.execute(
                    select(AvailabilityWindowModel).where(
                        AvailabilityWindowModel.workspace_id == workspace_id
                    )
                )
            ).scalars()
        )

        def _to_window(row: AvailabilityWindowModel) -> AvailabilityWindow:
            raw_tags: list[str] = (
                row.tags_json.get("tags", []) if isinstance(row.tags_json, dict) else []
            )
            return AvailabilityWindow(
                start_at=row.start_at,
                end_at=row.end_at,
                tags=frozenset(raw_tags),
            )

        availability = tuple(_to_window(row) for row in window_rows)

        task_rows = list(
            (
                await self._session.execute(
                    select(TaskModel).where(TaskModel.workspace_id == workspace_id)
                )
            ).scalars()
        )
        milestone_rows = list(
            (
                await self._session.execute(
                    select(MilestoneModel).where(MilestoneModel.workspace_id == workspace_id)
                )
            ).scalars()
        )
        calendar_rows = list(
            (
                await self._session.execute(
                    select(CalendarEventModel).where(
                        CalendarEventModel.workspace_id == workspace_id,
                        CalendarEventModel.sync_status != "tombstoned",
                    )
                )
            ).scalars()
        )
        dependency_rows = list(
            (
                await self._session.execute(
                    select(TaskDependencyModel).where(
                        TaskDependencyModel.workspace_id == workspace_id
                    )
                )
            ).scalars()
        )
        external_rows = list(
            (
                await self._session.execute(
                    select(ExternalDependencyModel).where(
                        ExternalDependencyModel.workspace_id == workspace_id
                    )
                )
            ).scalars()
        )
        external_task_rows = list(
            (
                await self._session.execute(
                    select(ExternalDependencyTaskModel).where(
                        ExternalDependencyTaskModel.workspace_id == workspace_id
                    )
                )
            ).scalars()
        )
        excluded_rows = list(
            (
                await self._session.execute(
                    select(WorkspaceExcludedDateModel).where(
                        WorkspaceExcludedDateModel.workspace_id == workspace_id
                    )
                )
            ).scalars()
        )
        linked_tasks: dict[UUID, dict[str, list[TaskId]]] = {}
        for row in external_task_rows:
            linked_tasks.setdefault(row.external_dependency_id, {}).setdefault(row.role, []).append(
                TaskId(row.task_id)
            )
        external_dependencies = tuple(
            ExternalDependencySnapshot(
                id=ExternalDependencyId(row.id),
                workspace_id=WorkspaceId(row.workspace_id),
                deliverable=row.deliverable,
                owner_label=row.owner_label,
                expected_delivery_at=row.expected_delivery_at,
                uncertainty_buffer_minutes=row.uncertainty_buffer_minutes,
                fallback_available=row.fallback_available,
                fallback_task_ids=tuple(
                    sorted(
                        linked_tasks.get(row.id, {}).get("fallback", []),
                        key=lambda task_id: task_id.value.hex,
                    )
                ),
                affected_task_ids=tuple(
                    sorted(
                        linked_tasks.get(row.id, {}).get("affected", []),
                        key=lambda task_id: task_id.value.hex,
                    )
                ),
                version=row.version,
            )
            for row in external_rows
        )
        latest = await PlanningRepository(self._session).latest_valid_plan(workspace_id)

        return PlannerInput(
            planner_version=PLANNER_VERSION,
            now_utc=now_utc,
            user_timezone=workspace.timezone,
            horizon_end_utc=now_utc + _horizon_span(milestone_rows, now_utc),
            slot_minutes=15,
            availability_windows=availability,
            calendar_events=tuple(_calendar_snapshot_from_model(row) for row in calendar_rows),
            tasks=tuple(_task_snapshot_from_model(row) for row in task_rows),
            milestones=tuple(_milestone_snapshot_from_model(row) for row in milestone_rows),
            task_dependencies=tuple(
                TaskDependency(
                    predecessor_id=TaskId(row.predecessor_id),
                    successor_id=TaskId(row.successor_id),
                    dependency_type=DependencyType(row.dependency_type),
                )
                for row in dependency_rows
            ),
            external_dependencies=external_dependencies,
            pinned_task_ids=frozenset(TaskId(row.id) for row in task_rows if row.pinned),
            excluded_dates=tuple(sorted(row.excluded_date for row in excluded_rows)),
            prior_plan_snapshot=(
                _prior_snapshot_from_model(latest) if latest is not None else None
            ),
        )

    async def create_plan(
        self,
        *,
        actor_user_id: UUID | None,
        workspace_id: UUID | str,
        reason: str = "manual",
    ) -> PlanSnapshotDTO:
        started = time.perf_counter()
        result = "ERROR"
        try:
            snapshot = await self._create_plan(
                actor_user_id=actor_user_id,
                workspace_id=workspace_id,
                reason=reason,
            )
            result = snapshot.status
            if snapshot.is_current:
                RUNTIME_METRICS.increment("plan_snapshots_appended_total")
            return snapshot
        finally:
            RUNTIME_METRICS.increment("planner_runs_total", result=result)
            RUNTIME_METRICS.observe(
                "planner_latency_seconds",
                max(0.0, time.perf_counter() - started),
                result=result,
            )

    async def _create_plan(
        self,
        *,
        actor_user_id: UUID | None,
        workspace_id: UUID | str,
        reason: str = "manual",
    ) -> PlanSnapshotDTO:
        """Append a snapshot only for valid outputs; failures preserve history."""
        workspace_uuid = workspace_id if isinstance(workspace_id, UUID) else UUID(str(workspace_id))
        now_utc = datetime.now(UTC)
        planner_input = await self._build_planner_input(workspace_uuid, now_utc)

        normalized = normalize_and_validate(planner_input)

        from personal_pm_planner.normalization.validate import InvalidPlannerInput

        if isinstance(normalized, InvalidPlannerInput):
            # PLAN-009: keep the last valid current snapshot untouched.
            latest = await self.latest_valid(workspace_uuid)
            prior_hash = latest.input_hash if latest else ""
            digest_source = f"{prior_hash}:{','.join(normalized.rule_ids)}"
            fake_hash = __import__("hashlib").sha256(digest_source.encode()).hexdigest()
            return PlanSnapshotDTO(
                id="",
                status="INVALID_INPUT",
                planner_version=PLANNER_VERSION,
                input_hash=fake_hash,
                is_current=False,
            )

        output = self._run_planner(planner_input)

        repo = PlanningRepository(self._session)
        previous_current = await repo.latest_valid_plan(workspace_uuid)
        if previous_current is not None:
            previous_current.is_current = False

        snapshot = PlanSnapshotModel(
            id=uuid4(),
            workspace_id=workspace_uuid,
            planner_version=output.planner_version,
            input_hash=output.input_hash,
            reason=reason,
            output_json=output.canonical_core(),
            is_current=True,
        )
        self._session.add(snapshot)
        await self._session.commit()

        return PlanSnapshotDTO(
            id=str(snapshot.id),
            status="OK",
            planner_version=snapshot.planner_version,
            input_hash=snapshot.input_hash,
            is_current=True,
        )

    def _run_planner(self, planner_input: PlannerInput) -> PlannerOutput:
        from personal_pm_planner import plan as run_plan

        return run_plan(planner_input)

    async def latest_valid(self, workspace_id: UUID | str) -> PlanSnapshotModel | None:
        repo = PlanningRepository(self._session)
        wid = workspace_id if isinstance(workspace_id, UUID) else UUID(str(workspace_id))
        return await repo.latest_valid_plan(wid)


def _horizon_span(milestone_rows: list[MilestoneModel], now_utc: datetime) -> timedelta:
    from datetime import timedelta

    latest = [m.deadline_at or m.deadline_date for m in milestone_rows]
    dated = [value for value in latest if value is not None]
    end_candidates = []
    for value in dated:
        try:
            end_candidates.append(
                value
                if isinstance(value, datetime)
                else datetime.combine(value, datetime.min.time(), tzinfo=UTC)
            )
        except TypeError:
            continue
    horizon = max(end_candidates) if end_candidates else now_utc + timedelta(days=14)
    if horizon <= now_utc:
        horizon = now_utc + timedelta(days=1)
    return horizon - now_utc
