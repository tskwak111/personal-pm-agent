"""Immutable plan snapshots backed by the pure planner.

A failed normalization or planning run NEVER replaces the last validated
current snapshot (PLAN-009); only fully valid outputs append history.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from personal_pm_planner.contracts.input import PlannerInput
from personal_pm_planner.contracts.output import PlannerOutput
from personal_pm_planner.domain.availability import AvailabilityWindow
from personal_pm_planner.domain.identifiers import (
    MilestoneId,
    TaskId,
    WorkspaceId,
    WorkstreamId,
)
from personal_pm_planner.domain.task import TaskSnapshot
from personal_pm_planner.domain.work import MilestoneSnapshot
from personal_pm_planner.normalization.validate import normalize_and_validate
from sqlalchemy import select

# Full registry import: ORM FK resolution needs every mapped table loaded.
from personal_pm_api.approvals import models as _approvals_m  # noqa: F401
from personal_pm_api.audit import models as _audit_m  # noqa: F401
from personal_pm_api.execution import models as _execution_m  # noqa: F401
from personal_pm_api.identity import models as _identity_m  # noqa: F401
from personal_pm_api.workspaces import models as _workspaces_m  # noqa: F401
from personal_pm_api.planning.models import (
    AvailabilityWindowModel,
    MilestoneModel,
    PlanSnapshotModel,
    TaskModel,
)
from personal_pm_api.planning.repository import PlanningRepository
from personal_pm_api.planning.schemas import PlanSnapshotDTO

PLANNER_VERSION = "planner-spec-1.0"
DEFAULT_USER_TIMEZONE = "Asia/Seoul"


def _task_snapshot_from_model(model: TaskModel) -> TaskSnapshot:
    return TaskSnapshot(
        id=TaskId(model.id),
        workspace_id=WorkspaceId(model.workspace_id),
        workstream_id=WorkstreamId(model.workstream_id),
        milestone_id=MilestoneId(model.milestone_id) if model.milestone_id else None,
        title=model.title,
        status=model.status,
        deadline_date=model.deadline_date,
        deadline_at=model.deadline_at,
        deadline_time_known=model.deadline_time_known,
        start_after=model.start_after,
        base_duration_minutes=model.base_duration_minutes,
        safety_duration_minutes=model.safety_duration_minutes,
        remaining_base_minutes=model.remaining_base_minutes,
        remaining_safety_minutes=model.remaining_safety_minutes,
        uncertainty=model.uncertainty,
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
        deadline_type=model.deadline_type,
        required_buffer_minutes=model.required_buffer_minutes,
        version=model.version,
    )


class PlanningService:
    def __init__(self, session) -> None:
        self._session = session

    async def _build_planner_input(self, workspace_id: UUID, now_utc: datetime) -> PlannerInput:
        window_rows = list(
            (
                await self._session.execute(
                    select(AvailabilityWindowModel).where(
                        AvailabilityWindowModel.workspace_id == workspace_id
                    )
                )
            ).scalars()
        )
        availability = tuple(
            AvailabilityWindow(
                start_at=row.start_at,
                end_at=row.end_at,
                tags=frozenset(row.tags_json.get("tags", [])),
            )
            for row in window_rows
        )

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

        return PlannerInput(
            planner_version=PLANNER_VERSION,
            now_utc=now_utc,
            user_timezone=DEFAULT_USER_TIMEZONE,
            horizon_end_utc=now_utc + _horizon_span(milestone_rows, now_utc),
            slot_minutes=15,
            availability_windows=availability,
            calendar_events=(),
            tasks=tuple(_task_snapshot_from_model(row) for row in task_rows),
            milestones=tuple(_milestone_snapshot_from_model(row) for row in milestone_rows),
            task_dependencies=(),
            external_dependencies=(),
            pinned_task_ids=frozenset(),
            excluded_dates=(),
        )

    async def create_plan(
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

    async def latest_valid(self, workspace_id):
        repo = PlanningRepository(self._session)
        wid = workspace_id if isinstance(workspace_id, UUID) else UUID(str(workspace_id))
        return await repo.latest_valid_plan(wid)


def _horizon_span(milestone_rows, now_utc: datetime):
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
