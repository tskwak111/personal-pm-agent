"""Workspace-filtered SQL projections for browser views."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.identity.session import CurrentActor
from personal_pm_api.views.schemas import (
    CalendarConnectionSummary,
    CalendarEventSummary,
    CalendarResponse,
    ExternalDependencySummary,
    FixedEvent,
    InboxCandidate,
    InboxResponse,
    MilestoneSummary,
    ProjectDetailResponse,
    ProjectsResponse,
    ProjectSummary,
    ProposalSummary,
    ReviewResponse,
    TaskSummary,
    TodayResponse,
)


def _task_summary(row: Any) -> TaskSummary:
    return TaskSummary(
        id=str(row.id),
        title=row.title,
        status=row.status,
        remaining_minutes=row.remaining_base_minutes,
        version=row.version,
    )


def _uuid_list(value: object) -> list[UUID]:
    if not isinstance(value, list):
        return []
    result: list[UUID] = []
    for item in value:
        if not isinstance(item, str):
            continue
        try:
            result.append(UUID(item))
        except ValueError:
            continue
    return result


def _today_payload(output: dict[str, object]) -> dict[str, object]:
    value = output.get("today")
    return value if isinstance(value, dict) else {}


async def _workspace_timezone(session: AsyncSession, workspace_id: UUID) -> ZoneInfo:
    from personal_pm_api.workspaces.models import WorkspaceModel

    workspace = await session.get(WorkspaceModel, workspace_id)
    return ZoneInfo(workspace.timezone if workspace is not None else "UTC")


async def _ordered_tasks(
    session: AsyncSession,
    workspace_id: UUID,
    task_ids: list[UUID],
) -> list[TaskSummary]:
    if not task_ids:
        return []
    from personal_pm_api.planning.models import TaskModel

    rows = list(
        (
            await session.execute(
                select(TaskModel).where(
                    TaskModel.workspace_id == workspace_id,
                    TaskModel.id.in_(task_ids),
                )
            )
        ).scalars()
    )
    by_id = {row.id: row for row in rows}
    return [_task_summary(by_id[item]) for item in task_ids if item in by_id]


async def today_view(session: AsyncSession, actor: CurrentActor) -> TodayResponse:
    from personal_pm_api.planning.models import CalendarEventModel, PlanSnapshotModel

    workspace_id = actor.workspace_id
    timezone = await _workspace_timezone(session, workspace_id)
    local_date = datetime.now(UTC).astimezone(timezone).date()
    day_start = datetime.combine(local_date, time.min, timezone).astimezone(UTC)
    day_end = datetime.combine(local_date + timedelta(days=1), time.min, timezone).astimezone(UTC)
    snapshot = (
        await session.execute(
            select(PlanSnapshotModel).where(
                PlanSnapshotModel.workspace_id == workspace_id,
                PlanSnapshotModel.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    event_rows = list(
        (
            await session.execute(
                select(CalendarEventModel)
                .where(
                    CalendarEventModel.workspace_id == workspace_id,
                    CalendarEventModel.sync_status != "tombstoned",
                    CalendarEventModel.event_kind.like("fixed%"),
                    CalendarEventModel.end_at > day_start,
                    CalendarEventModel.start_at < day_end,
                )
                .order_by(CalendarEventModel.start_at)
            )
        ).scalars()
    )
    fixed_events = [
        FixedEvent(
            id=str(row.id),
            title=row.title,
            start_at=row.start_at,
            end_at=row.end_at,
            kind=row.event_kind,
            sync_status=row.sync_status,
        )
        for row in event_rows
    ]
    if snapshot is None:
        return TodayResponse(
            plan_status="EMPTY",
            core_outcome=None,
            fixed_events=fixed_events,
            must_do=[],
            queue=[],
            not_today=[],
        )

    today = _today_payload(snapshot.output_json)
    must_ids = _uuid_list(today.get("must_do"))
    queue_ids = [
        *_uuid_list(today.get("next_queue")),
        *_uuid_list(today.get("opportunistic")),
    ]
    excluded_ids = _uuid_list(today.get("excluded"))
    core_ids = _uuid_list([today.get("core_result_task_id")])
    core = await _ordered_tasks(session, workspace_id, core_ids)
    return TodayResponse(
        plan_status="READY",
        core_outcome=core[0] if core else None,
        fixed_events=fixed_events,
        must_do=await _ordered_tasks(session, workspace_id, must_ids),
        queue=await _ordered_tasks(session, workspace_id, queue_ids),
        not_today=await _ordered_tasks(session, workspace_id, excluded_ids),
    )


async def inbox_view(session: AsyncSession, actor: CurrentActor) -> InboxResponse:
    from personal_pm_api.inbox.models import CandidateFactModel, InboxItemModel

    rows = (
        await session.execute(
            select(CandidateFactModel, InboxItemModel)
            .join(InboxItemModel, InboxItemModel.id == CandidateFactModel.inbox_item_id)
            .where(
                InboxItemModel.workspace_id == actor.workspace_id,
                CandidateFactModel.decision == "HOLD",
            )
            .order_by(CandidateFactModel.created_at)
        )
    ).all()
    return InboxResponse(
        candidates=[
            InboxCandidate(
                id=str(candidate.id),
                inbox_item_id=str(item.id),
                kind=candidate.kind,
                status=item.status,
                source_text=item.raw_text,
                interpretation=candidate.payload_json,
                evidence_score=candidate.evidence_score,
                decision=candidate.decision,
            )
            for candidate, item in rows
        ]
    )


async def _project_rows(
    session: AsyncSession, workspace_id: UUID
) -> tuple[list[Any], list[Any], list[Any], dict[str, object]]:
    from personal_pm_api.planning.models import (
        MilestoneModel,
        PlanSnapshotModel,
        TaskModel,
        WorkstreamModel,
    )

    workstreams = list(
        (
            await session.execute(
                select(WorkstreamModel)
                .where(WorkstreamModel.workspace_id == workspace_id)
                .order_by(WorkstreamModel.name)
            )
        ).scalars()
    )
    milestones = list(
        (
            await session.execute(
                select(MilestoneModel).where(MilestoneModel.workspace_id == workspace_id)
            )
        ).scalars()
    )
    tasks = list(
        (
            await session.execute(select(TaskModel).where(TaskModel.workspace_id == workspace_id))
        ).scalars()
    )
    snapshot = (
        await session.execute(
            select(PlanSnapshotModel).where(
                PlanSnapshotModel.workspace_id == workspace_id,
                PlanSnapshotModel.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    return workstreams, milestones, tasks, snapshot.output_json if snapshot else {}


def _risk_by_milestone(output: dict[str, object]) -> dict[UUID, tuple[str, list[str]]]:
    raw = output.get("risks")
    if not isinstance(raw, list):
        return {}
    result: dict[UUID, tuple[str, list[str]]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        milestone_id = item.get("milestone_id")
        level = item.get("level")
        if not isinstance(milestone_id, str) or not isinstance(level, str):
            continue
        try:
            key = UUID(milestone_id)
        except ValueError:
            continue
        reasons = item.get("reasons")
        result[key] = (
            level,
            [reason for reason in reasons if isinstance(reason, str)]
            if isinstance(reasons, list)
            else [],
        )
    return result


def _project_summary(
    workstream: Any,
    milestones: list[Any],
    tasks: list[Any],
    risks: dict[UUID, tuple[str, list[str]]],
) -> ProjectSummary:
    project_tasks = [row for row in tasks if row.workstream_id == workstream.id]
    done = sum(row.status == "done" for row in project_tasks)
    progress = round(done * 100 / len(project_tasks)) if project_tasks else 0
    milestone_ids = {row.id for row in milestones if row.workstream_id == workstream.id}
    risk_values = [risks[item] for item in milestone_ids if item in risks]
    rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    level, reasons = (
        max(risk_values, key=lambda value: rank.get(value[0], 0))
        if risk_values
        else (
            "UNASSESSED",
            [],
        )
    )
    return ProjectSummary(
        id=str(workstream.id),
        title=workstream.name,
        status=workstream.status,
        execution_progress=progress,
        risk_level=level,
        risk_reasons=reasons,
        task_count=len(project_tasks),
        done_count=done,
    )


async def projects_view(session: AsyncSession, actor: CurrentActor) -> ProjectsResponse:
    workstreams, milestones, tasks, output = await _project_rows(session, actor.workspace_id)
    risks = _risk_by_milestone(output)
    return ProjectsResponse(
        projects=[
            _project_summary(workstream, milestones, tasks, risks) for workstream in workstreams
        ]
    )


async def project_detail_view(
    session: AsyncSession,
    actor: CurrentActor,
    workstream_id: str,
) -> ProjectDetailResponse | None:
    from personal_pm_api.planning.models import (
        ExternalDependencyModel,
        ExternalDependencyTaskModel,
    )

    try:
        requested_id = UUID(workstream_id)
    except ValueError:
        return None
    workstreams, milestones, tasks, output = await _project_rows(session, actor.workspace_id)
    workstream = next((row for row in workstreams if row.id == requested_id), None)
    if workstream is None:
        return None
    project_milestones = [row for row in milestones if row.workstream_id == requested_id]
    project_tasks = [row for row in tasks if row.workstream_id == requested_id]
    project_task_ids = [row.id for row in project_tasks]
    dependencies = (
        list(
            (
                await session.execute(
                    select(ExternalDependencyModel)
                    .join(
                        ExternalDependencyTaskModel,
                        (
                            ExternalDependencyTaskModel.external_dependency_id
                            == ExternalDependencyModel.id
                        )
                        & (
                            ExternalDependencyTaskModel.workspace_id
                            == ExternalDependencyModel.workspace_id
                        ),
                    )
                    .where(
                        ExternalDependencyModel.workspace_id == actor.workspace_id,
                        ExternalDependencyTaskModel.task_id.in_(project_task_ids),
                    )
                    .distinct()
                )
            ).scalars()
        )
        if project_task_ids
        else []
    )
    return ProjectDetailResponse(
        project=_project_summary(
            workstream, project_milestones, project_tasks, _risk_by_milestone(output)
        ),
        milestones=[
            MilestoneSummary(
                id=str(row.id),
                title=row.title,
                status=row.status,
                deadline_date=row.deadline_date,
                deadline_at=row.deadline_at,
                deadline_time_known=row.deadline_time_known,
                version=row.version,
            )
            for row in project_milestones
        ],
        tasks=[_task_summary(row) for row in project_tasks],
        external_dependencies=[
            ExternalDependencySummary(
                id=str(row.id),
                deliverable=row.deliverable,
                owner_label=row.owner_label,
                expected_delivery_at=row.expected_delivery_at,
                fallback_available=row.fallback_available,
                version=row.version,
            )
            for row in dependencies
        ],
    )


async def calendar_view(session: AsyncSession, actor: CurrentActor) -> CalendarResponse:
    from personal_pm_api.calendar.connections import CalendarConnectionModel
    from personal_pm_api.calendar.models import ExternalCalendarEventModel
    from personal_pm_api.planning.models import PlanSnapshotModel, TaskModel

    events = list(
        (
            await session.execute(
                select(ExternalCalendarEventModel)
                .where(ExternalCalendarEventModel.workspace_id == actor.workspace_id)
                .order_by(ExternalCalendarEventModel.start_at)
            )
        ).scalars()
    )
    connections = list(
        (
            await session.execute(
                select(CalendarConnectionModel).where(
                    CalendarConnectionModel.workspace_id == actor.workspace_id
                )
            )
        ).scalars()
    )
    snapshot = (
        await session.execute(
            select(PlanSnapshotModel).where(
                PlanSnapshotModel.workspace_id == actor.workspace_id,
                PlanSnapshotModel.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    allocated: set[UUID] = set()
    if snapshot is not None:
        raw_allocations = snapshot.output_json.get("base_allocations")
        if isinstance(raw_allocations, list):
            for allocation in raw_allocations:
                if isinstance(allocation, dict):
                    allocated.update(_uuid_list([allocation.get("task_id")]))
    tasks = list(
        (
            await session.execute(
                select(TaskModel)
                .where(
                    TaskModel.workspace_id == actor.workspace_id,
                    TaskModel.status.not_in(("done", "cancelled")),
                )
                .order_by(TaskModel.created_at)
            )
        ).scalars()
    )
    return CalendarResponse(
        connections=[
            CalendarConnectionSummary(provider=row.provider, mode=row.mode, status=row.status)
            for row in connections
        ],
        events=[
            CalendarEventSummary(
                id=str(row.id),
                title=row.title,
                start_at=row.start_at,
                end_at=row.end_at,
                all_day=row.all_day,
                kind="focus_block" if row.managed_focus_block else row.availability_type,
                sync_status=row.sync_status,
            )
            for row in events
        ],
        flexible_tasks=[_task_summary(row) for row in tasks if row.id not in allocated],
    )


async def review_view(session: AsyncSession, actor: CurrentActor) -> ReviewResponse:
    from personal_pm_api.analytics.models import WorkSessionModel
    from personal_pm_api.approvals.models import ProposalModel
    from personal_pm_api.planning.models import PlanSnapshotModel

    timezone = await _workspace_timezone(session, actor.workspace_id)
    local_now = datetime.now(UTC).astimezone(timezone)
    period_start = local_now.date() - timedelta(days=local_now.weekday())
    period_end = period_start + timedelta(days=7)
    start_utc = datetime.combine(period_start, time.min, timezone).astimezone(UTC)
    end_utc = datetime.combine(period_end, time.min, timezone).astimezone(UTC)
    snapshot = (
        await session.execute(
            select(PlanSnapshotModel).where(
                PlanSnapshotModel.workspace_id == actor.workspace_id,
                PlanSnapshotModel.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    planned = 0
    if snapshot is not None:
        raw_allocations = snapshot.output_json.get("base_allocations")
        if isinstance(raw_allocations, list):
            for item in raw_allocations:
                if not isinstance(item, dict):
                    continue
                start, end = item.get("start"), item.get("end")
                if not isinstance(start, str) or not isinstance(end, str):
                    continue
                try:
                    start_at = datetime.fromisoformat(start)
                    end_at = datetime.fromisoformat(end)
                except ValueError:
                    continue
                if start_at.tzinfo is None or end_at.tzinfo is None:
                    continue
                if start_utc <= start_at < end_utc and end_at > start_at:
                    planned += int((end_at - start_at).total_seconds() // 60)
    sessions = list(
        (
            await session.execute(
                select(WorkSessionModel).where(
                    WorkSessionModel.workspace_id == actor.workspace_id,
                    WorkSessionModel.started_at >= start_utc,
                    WorkSessionModel.started_at < end_utc,
                )
            )
        ).scalars()
    )
    proposals = list(
        (
            await session.execute(
                select(ProposalModel)
                .where(
                    ProposalModel.workspace_id == actor.workspace_id,
                    ProposalModel.status == "pending",
                )
                .order_by(ProposalModel.created_at)
            )
        ).scalars()
    )
    actual = sum(row.actual_focus_minutes for row in sessions)
    return ReviewResponse(
        period_start=period_start,
        period_end=period_end,
        planned_minutes=planned,
        actual_minutes=actual,
        missed_minutes=max(0, planned - actual),
        pending_proposals=[
            ProposalSummary(
                id=str(row.id),
                kind=row.kind,
                approval_level=row.approval_level,
                status=row.status,
                version=row.version,
                targets=row.targets_json,
            )
            for row in proposals
        ],
    )


__all__ = [
    "calendar_view",
    "inbox_view",
    "project_detail_view",
    "projects_view",
    "review_view",
    "today_view",
]
